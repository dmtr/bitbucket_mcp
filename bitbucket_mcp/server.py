"""MCP server with plugin-style auto-registration of tools and prompts.

Adding a new tool requires only:

1. A method on :class:`~bitbucket_mcp.client.BitbucketClient`.
2. A thin ``@bitbucket_tool``-decorated function whose signature defines the
   MCP input schema and whose body delegates to the client via :func:`_call`.

Prompts are registered automatically from :data:`~bitbucket_mcp.prompts.TOOL_PROMPTS`
— no separate ``@mcp.prompt()`` boilerplate needed.
"""

from __future__ import annotations

import functools
import json
import logging
from typing import Any, Callable, Optional

from mcp.server.fastmcp import FastMCP

from bitbucket_mcp.client import get_client
from bitbucket_mcp.diff_filter import DEFAULT_MAX_CHARS
from bitbucket_mcp.prompts import TOOL_PROMPTS

logger = logging.getLogger(__name__)

mcp = FastMCP("BitbucketMCP")

MAX_PAGE = 100


# ---------------------------------------------------------------------- #
# Consistent result / error handling
# ---------------------------------------------------------------------- #


def _call(
    method_name: str,
    empty_msg: str = "No results found.",
    *args: Any,
    raw: bool = False,
    **kwargs: Any,
) -> str:
    """Invoke a :class:`BitbucketClient` method with uniform handling.

    This centralises three concerns that were previously duplicated in every
    tool function:

    * **Client access** — uses the shared singleton instead of constructing a
      new ``BitbucketCodeSearch`` on each call.
    * **Error handling** — catches all exceptions and returns a readable error
      string instead of letting the MCP layer surface a raw traceback.
    * **Result formatting** — JSON-encodes dict/list results; returns strings
      as-is when *raw* is True (for file content / diffs).

    Args:
        method_name: Name of the method on :class:`BitbucketClient`.
        empty_msg: Message to return when the result is falsy.
        raw: If True, return string results without JSON encoding.
        *args, **kwargs: Forwarded to the client method.

    Returns:
        A string ready to be returned from an MCP tool.
    """
    try:
        client = get_client()
        result = getattr(client, method_name)(*args, **kwargs)
    except Exception as e:
        logger.error("Tool '%s' failed: %s", method_name, e, exc_info=True)
        return f"Error: {e}"

    if not result:
        return empty_msg

    if raw or isinstance(result, str):
        return result

    return json.dumps(result)


# ---------------------------------------------------------------------- #
# Plugin-style auto-registration
# ---------------------------------------------------------------------- #


def bitbucket_tool(
    method_name: str,
    *,
    empty_msg: str = "No results found.",
    raw: bool = False,
) -> Callable[[Callable], Callable]:
    """Decorator that registers a function as an MCP tool.

    The decorated function's **signature** is what matters — FastMCP uses it
    to derive the tool's JSON-schema input.  The function **body** delegates
    to the shared client instance via :func:`_call`.

    Prompts are registered *separately* and automatically from
    :data:`~bitbucket_mcp.prompts.TOOL_PROMPTS` — see
    :func:`_auto_register_prompts`.  Keeping prompt text in one place means
    adding a new prompt is a single-line edit in ``prompts.py``.

    Usage::

        @bitbucket_tool("get_commits", empty_msg="No commits found.")
        def bitbucket_get_commits(
            repo_slug: str,
            include: Optional[list[str]] = None,
            ...
        ) -> str:
            \\\"\\\"\\\"Get a list of commits from a Bitbucket repository.\\\"\\\"\\\"
            return _call("get_commits", "No commits found.",
                         repo_slug=repo_slug, include=include, ...)

    Args:
        method_name: Name of the :class:`BitbucketClient` method to call.
        empty_msg: Message returned when the client method yields a falsy result.
        raw: If True, string results are returned without JSON encoding.
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> str:
            # The wrapped function body already calls _call(); we keep the
            # wrapper so mcp.tool() sees the correct __name__ / __doc__ /
            # __annotations__ for schema generation.
            return fn(*args, **kwargs)

        mcp.tool()(wrapper)
        return wrapper

    return decorator


def _register_prompt(name: str, text: str) -> None:
    """Register a static-text MCP prompt under *name*."""

    @mcp.prompt(name=name)
    def _prompt() -> str:
        return text

    _prompt.__doc__ = text


def _auto_register_prompts() -> None:
    """Register all prompts defined in :data:`TOOL_PROMPTS`.

    This is the single registration point for prompts.  Each key in
    ``TOOL_PROMPTS`` becomes an MCP prompt named ``{key}_prompt``.  Adding a
    new prompt is as simple as adding an entry to the dict in ``prompts.py``.
    """
    for name, text in TOOL_PROMPTS.items():
        _register_prompt(f"{name}_prompt", text)


# ---------------------------------------------------------------------- #
# Tool definitions
#
# Each function below defines the MCP tool's input schema (via its signature)
# and delegates to the client through _call().  This is the single place to
# touch when adding or modifying a tool.
# ---------------------------------------------------------------------- #


@bitbucket_tool("code_search")
def bitbucket_code_search(
    search_query: str,
    page: int = 1,
    pagelen: int = 50,
) -> str:
    """
    Perform a code search in Bitbucket.

    Args:
        search_query: The search query string
        page: number of the page to fetch
        pagelen: number of items per page (default is 50)
    Returns:
        A string representation of the search results in JSON format
    """
    return _call(
        "code_search",
        "No results found.",
        search_query,
        page=page,
        pagelen=pagelen,
    )


@bitbucket_tool("get_repositories")
def bitbucket_get_repositories(
    search_query: Optional[str] = None,
    sort: Optional[str] = None,
    role: Optional[str] = None,
    page: int = 1,
    pagelen: int = 50,
) -> str:
    """
    Get list of repositories in a Bitbucket workspace.

    Args:
        search_query: Optional query string to filter repositories (e.g. 'name ~ "reportal-reports"')
        sort: Optional sort parameter (e.g., "-updated_on" or "-created_on")
        role: Optional filter by role (e.g., "admin", "contributor", "member")
        page: Number of the page to fetch
        pagelen: Number of items per page (default is 50)

    Returns:
        A string representation of the repositories in JSON format
    """
    return _call(
        "get_repositories",
        "No repositories found.",
        search_query=search_query,
        sort=sort,
        role=role,
        page=page,
        pagelen=pagelen,
    )


@bitbucket_tool("create_branch")
def bitbucket_create_branch(
    repo_slug: str,
    branch_name: str,
) -> str:
    """
    Create a new branch in a Bitbucket repository.

    Args:
        repo_slug: The slug of the repository where the branch will be created
        branch_name: The name of the new branch to be created
    Returns:
        A string representation of the branch creation result in JSON format
    """
    return _call(
        "create_branch",
        "Failed to create branch.",
        repo_slug,
        branch_name,
    )


@bitbucket_tool("get_commits")
def bitbucket_get_commits(
    repo_slug: str,
    include: Optional[list[str]] = None,
    exclude: Optional[list[str]] = None,
    path: Optional[str] = None,
    max_page: int = MAX_PAGE,
) -> str:
    """
    Get a list of commits from a Bitbucket repository.

    Args:
        repo_slug: The slug of the repository to get commits from
        include: Optional list of refs to include (e.g. ["master", "feature-branch"])
        exclude: Optional list of refs to exclude (e.g. ["dev"])
        path: Optional file or directory path to filter commits by
        max_page: Maximum number of pages to fetch
    Returns:
        A string representation of the commits in JSON format
    """
    return _call(
        "get_commits",
        "No commits found.",
        repo_slug,
        include=include,
        exclude=exclude,
        path=path,
        max_page=max_page,
    )


@bitbucket_tool("get_file_content", raw=True)
def bitbucket_get_file_content(
    repo_slug: str,
    commit: str,
    path: str,
) -> str:
    """
    Get the raw content of a file from a Bitbucket repository.

    Args:
        repo_slug: The slug of the repository containing the file
        commit: The commit or branch name (e.g. "master", "develop", or a commit hash)
        path: The path to the file within the repository
    Returns:
        The raw content of the file as a string
    """
    return _call(
        "get_file_content",
        "Error retrieving file content.",
        repo_slug,
        commit,
        path,
    )


@bitbucket_tool("create_pull_request")
def bitbucket_create_pr(
    repo_slug: str,
    branch_name: str,
    title: str,
    description: str,
    destination: str = "master",
) -> str:
    """
    Create a pull request in a Bitbucket repository.

    Args:
        repo_slug: The slug of the repository where the PR will be created
        branch_name: The name of the source branch for the PR
        title: The title of the pull request
        description: The description of the pull request
        destination: The destination branch for the PR (default is "master")
    Returns:
        A string indicating the success or failure of the pull request creation
    """
    result = _call(
        "create_pull_request",
        "Failed to create pull request.",
        repo_slug,
        branch_name,
        title,
        description,
        destination,
    )
    # create_pull_request returns a dict with 'success' key — format it
    # into a human-readable message for the MCP consumer.
    try:
        data = json.loads(result)
    except (json.JSONDecodeError, TypeError):
        return result

    if isinstance(data, dict) and "success" in data:
        if data["success"]:
            return (
                f"Pull request created successfully in repository "
                f"'{repo_slug}' from branch '{branch_name}' to '{destination}'."
            )
        return data.get("error", "Failed to create pull request.")

    return result


@bitbucket_tool("get_pull_requests")
def bitbucket_get_pull_requests(
    repo_slug: str,
    state: Optional[str] = None,
    page: int = 1,
    pagelen: int = 50,
) -> str:
    """
    List pull requests for a repository.

    Args:
        repo_slug: The slug of the repository.
        state: Optional pull request state filter (e.g., "OPEN", "MERGED", "DECLINED").
        page: Page number for pagination.
        pagelen: Number of results per page.
    Returns:
        A JSON string representing the list of pull request objects.
    """
    return _call(
        "get_pull_requests",
        "No pull requests found.",
        repo_slug,
        state=state,
        page=page,
        pagelen=pagelen,
    )


@bitbucket_tool("get_pull_request")
def bitbucket_get_pull_request(
    repo_slug: str,
    pull_request_id: int,
) -> str:
    """
    Retrieve a single pull request.

    Args:
        repo_slug: The slug of the repository.
        pull_request_id: The numeric ID of the pull request.
    Returns:
        A JSON string representing the pull request object, or an empty JSON object if not found.
    """
    return _call(
        "get_pull_request",
        "{}",
        repo_slug,
        pull_request_id,
    )


@bitbucket_tool("get_pull_request_diff", raw=True)
def bitbucket_get_pull_request_diff(
    repo_slug: str,
    pull_request_id: int,
    paths: Optional[list[str]] = None,
    exclude: Optional[list[str]] = None,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> str:
    """
    Get the diff for a pull request, optionally limited to some files.

    For large PRs, call bitbucket_get_pull_request_diffstat first, then fetch
    the files you need with `paths`.

    Args:
        repo_slug: The slug of the repository.
        pull_request_id: The numeric ID of the pull request.
        paths: Glob patterns (e.g. ["src/app/*.py", "README.md"]) matched against the
            file path or file name; only matching files are returned.
        exclude: Glob patterns of files to drop. Defaults to lock files (*.lock,
            package-lock.json, ...) unless `paths` is given; pass [] to keep everything.
        max_chars: Size budget for the file diffs (default 50000; 0 = no limit).
            Files that don't fit are skipped whole and listed at the end; the
            closing notes come on top of this budget.
    Returns:
        The diff as a string. Lines starting with "[bitbucket-mcp]" at the end
        list any files that were skipped, excluded, or omitted for size.
    """
    return _call(
        "get_pull_request_diff",
        "Error retrieving diff.",
        repo_slug,
        pull_request_id,
        paths=paths,
        exclude=exclude,
        max_chars=max_chars,
    )


@bitbucket_tool("get_pull_request_diffstat")
def bitbucket_get_pull_request_diffstat(
    repo_slug: str,
    pull_request_id: int,
) -> str:
    """
    List the files changed by a pull request, with line counts.

    Cheap overview to decide which files to read with bitbucket_get_pull_request_diff.

    Args:
        repo_slug: The slug of the repository.
        pull_request_id: The numeric ID of the pull request.
    Returns:
        JSON with files_changed, lines_added, lines_removed, and a `files` list of
        {path, status, lines_added, lines_removed[, old_path]}.
    """
    return _call(
        "get_pull_request_diffstat",
        "{}",
        repo_slug,
        pull_request_id,
    )


@bitbucket_tool("create_pull_request_comment")
def bitbucket_post_pr_comment(
    repo_slug: str,
    pull_request_id: int,
    content: str,
    file_path: Optional[str] = None,
    line: Optional[int] = None,
    line_type: Optional[str] = None,
) -> str:
    """
    Post a comment on a Bitbucket pull request.

    Omit file_path/line to post a general PR comment; provide them to anchor
    an inline comment to a diff line. `content` is Markdown.

    Args:
        repo_slug: The slug of the repository.
        pull_request_id: The numeric ID of the pull request.
        content: The comment text (Markdown).
        file_path: Optional path of the file for an inline comment.
        line: Diff line number an inline comment anchors to.
        line_type: "ADDED" (default), "REMOVED", or "CONTEXT". ADDED/CONTEXT
            anchor to the new side of the diff; REMOVED to the old side.
    Returns:
        A string indicating success (with the comment's web permalink) or
        failure with the API error message.
    """
    result = _call(
        "create_pull_request_comment",
        "Failed to post comment.",
        repo_slug,
        pull_request_id,
        content,
        file_path=file_path,
        line=line,
        line_type=line_type,
    )

    try:
        data = json.loads(result)
    except (json.JSONDecodeError, TypeError):
        return result

    if isinstance(data, dict) and "success" in data:
        if data["success"]:
            payload = data.get("data") or {}
            link = ""
            links = payload.get("links", {})
            if isinstance(links, dict):
                html = links.get("html", {})
                if isinstance(html, dict):
                    link = html.get("href", "")
            suffix = f": {link}" if link else ""
            return (
                f"Comment posted on pull request #{pull_request_id} "
                f"in repository '{repo_slug}'{suffix}."
            )
        return data.get("error", "Failed to post comment.")

    return result


@bitbucket_tool("get_pull_request_comments")
def bitbucket_get_pull_request_comments(
    repo_slug: str,
    pull_request_id: int,
    page: int = 1,
    pagelen: int = 50,
) -> str:
    """
    Get comments for a pull request.

    Args:
        repo_slug: The slug of the repository.
        pull_request_id: The numeric ID of the pull request.
        page: Page number for pagination.
        pagelen: Number of results per page.
    Returns:
        A JSON string representing the list of comment objects.
    """
    return _call(
        "get_pull_request_comments",
        "No comments found.",
        repo_slug,
        pull_request_id,
        page=page,
        pagelen=pagelen,
    )


# ---------------------------------------------------------------------- #
# Auto-register all prompts from TOOL_PROMPTS (single source of truth)
# ---------------------------------------------------------------------- #

_auto_register_prompts()


# ---------------------------------------------------------------------- #
# Entry point
# ---------------------------------------------------------------------- #


def main() -> None:
    """Run the MCP server (delegates to :mod:`bitbucket_mcp.__main__`)."""
    from bitbucket_mcp.__main__ import main as _main

    _main()
