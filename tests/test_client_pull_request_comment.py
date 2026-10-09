"""Tests for :meth:`BitbucketClient.create_pull_request_comment`."""

from types import SimpleNamespace
from typing import Any

from bitbucket_mcp.client import BitbucketClient
from bitbucket_mcp.config import BitbucketConfig

COMMENTS_URL = "/repositories/ws/repo/pullrequests/7/comments"


class FakeCloud:
    """Records post() calls and answers from a {url: response} mapping."""

    def __init__(self, responses: dict[str, Any]):
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def post(self, path: str, json: Any = None, headers: Any = None, advanced_mode: bool = False) -> Any:
        self.calls.append({"path": path, "json": json, "headers": headers})
        return self.responses[path]


def _client(responses: dict[str, Any]) -> BitbucketClient:
    client = BitbucketClient.__new__(BitbucketClient)
    client.config = BitbucketConfig(workspace="ws", access_token="token")
    client._client = FakeCloud(responses)
    return client


def _resp(status: int, payload: dict[str, Any] | None = None) -> SimpleNamespace:
    return SimpleNamespace(status_code=status, json=lambda: payload, text="body")


def test_general_comment_success():
    cloud_resp = _resp(
        201,
        {"id": 42, "links": {"html": {"href": "https://bb/.../c-42"}}},
    )
    client = _client({COMMENTS_URL: cloud_resp})

    result = client.create_pull_request_comment("repo", 7, "hello world")

    assert result == {
        "success": True,
        "data": {"id": 42, "links": {"html": {"href": "https://bb/.../c-42"}}},
    }
    assert client._client.calls == [
        {
            "path": COMMENTS_URL,
            "json": {"content": {"raw": "hello world"}},
            "headers": {"Accept": "application/json"},
        }
    ]


def test_inline_added_uses_to():
    cloud_resp = _resp(201, {"id": 1})
    client = _client({COMMENTS_URL: cloud_resp})

    client.create_pull_request_comment(
        "repo", 7, "nit", file_path="src/a.py", line=10
    )

    sent = client._client.calls[0]["json"]
    assert sent["inline"] == {"path": "src/a.py", "to": 10}


def test_inline_context_uses_to():
    cloud_resp = _resp(201, {"id": 1})
    client = _client({COMMENTS_URL: cloud_resp})

    client.create_pull_request_comment(
        "repo", 7, "ctx", file_path="src/a.py", line=5, line_type="CONTEXT"
    )

    sent = client._client.calls[0]["json"]
    assert sent["inline"] == {"path": "src/a.py", "to": 5}


def test_inline_removed_uses_from():
    cloud_resp = _resp(201, {"id": 1})
    client = _client({COMMENTS_URL: cloud_resp})

    client.create_pull_request_comment(
        "repo", 7, "gone", file_path="src/a.py", line=8, line_type="removed"
    )

    sent = client._client.calls[0]["json"]
    assert sent["inline"] == {"path": "src/a.py", "from": 8}


def test_unknown_line_type_falls_back_to_added():
    cloud_resp = _resp(201, {"id": 1})
    client = _client({COMMENTS_URL: cloud_resp})

    client.create_pull_request_comment(
        "repo", 7, "x", file_path="src/a.py", line=3, line_type="bogus"
    )

    sent = client._client.calls[0]["json"]
    assert sent["inline"] == {"path": "src/a.py", "to": 3}


def test_file_path_without_line_posts_general_comment():
    cloud_resp = _resp(201, {"id": 1})
    client = _client({COMMENTS_URL: cloud_resp})

    client.create_pull_request_comment("repo", 7, "x", file_path="src/a.py")

    sent = client._client.calls[0]["json"]
    assert "inline" not in sent
    assert sent == {"content": {"raw": "x"}}


def test_error_status_returned():
    cloud_resp = _resp(400)
    client = _client({COMMENTS_URL: cloud_resp})

    result = client.create_pull_request_comment("repo", 7, "bad", file_path="x.py", line=1)

    assert result["success"] is False
    assert result["error"].startswith("Failed to post comment (status 400):")
