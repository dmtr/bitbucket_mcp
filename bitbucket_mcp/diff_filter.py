"""Split a unified git diff into per-file chunks and filter them.

Large pull request diffs often exceed what an MCP client accepts in a single
tool result, and lock files make up a big share of that noise.  The helpers
here let the diff tool return only the files that matter, and always say which
files were left out so the caller can fetch them explicitly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import Optional

DEFAULT_EXCLUDE: tuple[str, ...] = (
    "*.lock",
    "package-lock.json",
    "npm-shrinkwrap.json",
    "pnpm-lock.yaml",
    "go.sum",
)

DEFAULT_MAX_CHARS = 50_000

_FILE_HEADER = re.compile(r"^diff --git a/(.+?) b/(.+)$", re.MULTILINE)
_NOTE_PREFIX = "[bitbucket-mcp]"


@dataclass(frozen=True)
class FileDiff:
    """The diff of a single file, as found in a unified git diff."""

    old_path: str
    new_path: str
    text: str

    def matches(self, patterns: list[str] | tuple[str, ...]) -> bool:
        """True if either path, or its file name, matches any glob pattern."""
        candidates = {self.old_path, self.new_path}
        candidates |= {path.rsplit("/", 1)[-1] for path in candidates}
        return any(fnmatchcase(candidate, pattern) for candidate in candidates for pattern in patterns)


def split_diff(diff: str) -> tuple[str, list[FileDiff]]:
    """Split *diff* into the text before the first file header and one :class:`FileDiff` per file."""
    headers = list(_FILE_HEADER.finditer(diff))
    if not headers:
        return diff, []

    preamble = diff[: headers[0].start()]
    ends = [header.start() for header in headers[1:]] + [len(diff)]
    files = [
        FileDiff(old_path=header.group(1), new_path=header.group(2), text=diff[header.start() : end])
        for header, end in zip(headers, ends)
    ]
    return preamble, files


def filter_diff(
    diff: str,
    paths: Optional[list[str]] = None,
    exclude: Optional[list[str]] = None,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> str:
    """Keep only the wanted file diffs and append notes about anything left out.

    Args:
        diff: Full unified diff.
        paths: Glob patterns; when given, only matching files are kept.
        exclude: Glob patterns of files to drop.  ``None`` means
            :data:`DEFAULT_EXCLUDE` when *paths* is not given (explicitly
            requested files are never dropped by the defaults); pass ``[]``
            to keep lock files.
        max_chars: Budget for the returned file diffs; files that don't fit are
            skipped whole and listed in a note.  ``0`` disables the limit.

    Returns:
        The filtered diff, followed by ``[bitbucket-mcp]`` notes when files were dropped.
    """
    if exclude is not None:
        exclude_patterns: tuple[str, ...] = tuple(exclude)
    else:
        exclude_patterns = () if paths else DEFAULT_EXCLUDE
    preamble, files = split_diff(diff)
    if not files:
        return diff

    kept: list[FileDiff] = []
    not_in_paths: list[FileDiff] = []
    excluded: list[FileDiff] = []
    over_budget: list[FileDiff] = []
    used = len(preamble)
    for file_diff in files:
        if paths and not file_diff.matches(paths):
            not_in_paths.append(file_diff)
        elif file_diff.matches(exclude_patterns):
            excluded.append(file_diff)
        elif max_chars and used + len(file_diff.text) > max_chars:
            over_budget.append(file_diff)
        else:
            kept.append(file_diff)
            used += len(file_diff.text)

    notes = []
    if not_in_paths:
        notes.append(f"{_NOTE_PREFIX} Skipped {len(not_in_paths)} file(s) not matching `paths`.")
    if excluded:
        names = ", ".join(f.new_path for f in excluded)
        notes.append(
            f"{_NOTE_PREFIX} Excluded {len(excluded)} file(s) by `exclude` patterns (pass exclude=[] to include): {names}"
        )
    if over_budget:
        names = ", ".join(f"{f.new_path} ({len(f.text):,} chars)" for f in over_budget)
        notes.append(
            f"{_NOTE_PREFIX} Omitted {len(over_budget)} file(s) to stay under max_chars={max_chars:,};"
            f" fetch them with `paths` or a larger `max_chars`: {names}"
        )

    body = preamble + "".join(f.text for f in kept)
    if not kept:
        body = f"{_NOTE_PREFIX} No file diffs to show.\n"
    if not notes:
        return body
    return body.rstrip("\n") + "\n\n" + "\n".join(notes) + "\n"
