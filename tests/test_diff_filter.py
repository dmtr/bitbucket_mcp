import pytest

from bitbucket_mcp.diff_filter import filter_diff, split_diff


def _file_diff(path: str, body: str = "+added\n", old_path: str | None = None) -> str:
    old_path = old_path or path
    return f"diff --git a/{old_path} b/{path}\n--- a/{old_path}\n+++ b/{path}\n@@ -1 +1 @@\n{body}"


APP = _file_diff("src/app.py")
README = _file_diff("README.md")
POETRY_LOCK = _file_diff("poetry.lock", "+" + "x" * 500 + "\n")
NESTED_LOCK = _file_diff("web/yarn.lock")
DIFF = APP + POETRY_LOCK + README + NESTED_LOCK


def _notes(output: str) -> list[str]:
    return [line for line in output.splitlines() if line.startswith("[bitbucket-mcp]")]


def test_split_diff_returns_one_chunk_per_file():
    preamble, files = split_diff(DIFF)

    assert preamble == ""
    assert [f.new_path for f in files] == ["src/app.py", "poetry.lock", "README.md", "web/yarn.lock"]
    assert "".join(f.text for f in files) == DIFF


def test_split_diff_keeps_old_path_of_renamed_files():
    _, [renamed] = split_diff(_file_diff("src/new.py", old_path="src/old.py"))

    assert (renamed.old_path, renamed.new_path) == ("src/old.py", "src/new.py")


def test_lock_files_are_excluded_by_default_and_listed():
    output = filter_diff(DIFF)

    assert output.startswith(APP + README.rstrip("\n"))
    assert "poetry.lock" not in output.split("[bitbucket-mcp]")[0]
    assert _notes(output) == [
        "[bitbucket-mcp] Excluded 2 file(s) by `exclude` patterns (pass exclude=[] to include): "
        "poetry.lock, web/yarn.lock"
    ]


def test_empty_exclude_keeps_everything():
    assert filter_diff(DIFF, exclude=[]) == DIFF


def test_paths_select_files_by_glob_and_are_not_dropped_by_default_excludes():
    output = filter_diff(DIFF, paths=["src/*", "poetry.lock"])

    assert output.startswith(APP + POETRY_LOCK.rstrip("\n"))
    assert _notes(output) == ["[bitbucket-mcp] Skipped 2 file(s) not matching `paths`."]


def test_explicit_exclude_applies_together_with_paths():
    output = filter_diff(DIFF, paths=["*.py", "*.md"], exclude=["README.md"])

    assert output.startswith(APP.rstrip("\n"))
    assert "Excluded 1 file(s)" in _notes(output)[1]


def test_paths_match_the_old_path_of_renamed_files():
    renamed = _file_diff("src/new.py", old_path="src/old.py")

    assert filter_diff(renamed + README, paths=["src/old.py"]).startswith(renamed)


def test_files_over_budget_are_skipped_whole_and_smaller_ones_still_fit():
    big = _file_diff("src/big.py", "+" + "y" * 1_000 + "\n")
    max_chars = len(APP) + len(README)

    output = filter_diff(APP + big + README, max_chars=max_chars)

    assert output.startswith(APP + README.rstrip("\n"))
    [note] = _notes(output)
    assert note.startswith(f"[bitbucket-mcp] Omitted 1 file(s) to stay under max_chars={max_chars:,};")
    assert note.endswith(f"src/big.py ({len(big):,} chars)")


def test_zero_max_chars_disables_the_limit():
    assert filter_diff(DIFF, exclude=[], max_chars=0) == DIFF


def test_reports_when_no_file_is_left():
    output = filter_diff(DIFF, paths=["nothing/*"])

    assert output.startswith("[bitbucket-mcp] No file diffs to show.")
    assert len(_notes(output)) == 2


@pytest.mark.parametrize("diff", ["", "not a git diff"])
def test_text_without_file_headers_is_returned_unchanged(diff):
    assert filter_diff(diff) == diff
