from types import SimpleNamespace
from typing import Any

import pytest

from bitbucket_mcp.client import BitbucketClient
from bitbucket_mcp.config import BitbucketConfig

PR_URL = "/repositories/ws/repo/pullrequests/7"
NEXT_URL = "https://api.bitbucket.org/2.0/repositories/ws/repo/diffstat/ws/repo:aaa%0Dbbb?page=2"


class FakeCloud:
    """Records calls and answers them from a {url: response} mapping."""

    def __init__(self, responses: dict[str, Any]):
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def get(self, path: str, params: Any = None, advanced_mode: bool = False, absolute: bool = False) -> Any:
        self.calls.append({"path": path, "params": params, "absolute": absolute})
        return self.responses[path]


def _client(responses: dict[str, Any]) -> BitbucketClient:
    client = BitbucketClient.__new__(BitbucketClient)
    client.config = BitbucketConfig(workspace="ws", access_token="token")
    client._client = FakeCloud(responses)
    return client


def _entry(status: str, old: str | None, new: str | None, added: int, removed: int) -> dict[str, Any]:
    return {
        "type": "diffstat",
        "status": status,
        "old": {"path": old, "type": "commit_file"} if old else None,
        "new": {"path": new, "type": "commit_file"} if new else None,
        "lines_added": added,
        "lines_removed": removed,
    }


def test_diffstat_follows_next_links_and_compacts_entries():
    client = _client(
        {
            f"{PR_URL}/diffstat": {
                "values": [_entry("modified", "a.py", "a.py", 3, 1), _entry("added", None, "b.py", 10, 0)],
                "next": NEXT_URL,
            },
            NEXT_URL: {
                "values": [_entry("removed", "c.py", None, 0, 4), _entry("renamed", "old.py", "new.py", 1, 1)],
            },
        }
    )

    result = client.get_pull_request_diffstat("repo", 7)

    assert result == {
        "files_changed": 4,
        "lines_added": 14,
        "lines_removed": 6,
        "files": [
            {"path": "a.py", "status": "modified", "lines_added": 3, "lines_removed": 1},
            {"path": "b.py", "status": "added", "lines_added": 10, "lines_removed": 0},
            {"path": "c.py", "status": "removed", "lines_added": 0, "lines_removed": 4},
            {"path": "new.py", "status": "renamed", "lines_added": 1, "lines_removed": 1, "old_path": "old.py"},
        ],
    }
    assert client.client.calls[1] == {"path": NEXT_URL, "params": None, "absolute": True}


def test_diffstat_stops_at_max_page(caplog):
    client = _client({f"{PR_URL}/diffstat": {"values": [_entry("added", None, "a.py", 1, 0)], "next": NEXT_URL}})

    result = client.get_pull_request_diffstat("repo", 7, max_page=1)

    assert result["files_changed"] == 1
    assert len(client.client.calls) == 1
    assert "maximum page limit" in caplog.text


def test_diff_is_filtered():
    diff = "diff --git a/a.py b/a.py\n+x\ndiff --git a/uv.lock b/uv.lock\n+y\n"
    client = _client({f"{PR_URL}/diff": SimpleNamespace(status_code=200, text=diff)})

    output = client.get_pull_request_diff("repo", 7)

    assert output.startswith("diff --git a/a.py b/a.py\n+x\n")
    assert "Excluded 1 file(s)" in output


@pytest.mark.parametrize("response", [SimpleNamespace(status_code=404, text="nope"), None])
def test_diff_errors_are_reported(response):
    client = _client({f"{PR_URL}/diff": response})

    assert client.get_pull_request_diff("repo", 7).startswith("Error retrieving diff")
