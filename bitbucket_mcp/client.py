"""Bitbucket Cloud API client.

This module wraps :class:`atlassian.bitbucket.cloud.Cloud` and exposes
high-level methods used by the MCP tool layer (:mod:`bitbucket_mcp.server`).

Key improvements over the original monolithic ``server.py``:

* **Renamed** from ``BitbucketCodeSearch`` → :class:`BitbucketClient` (the class
  does far more than code search).
* **Shared instance** — :func:`get_client` lazily creates a single client,
  avoiding a new ``Cloud`` connection on every tool call.
* **Unified pagination** — :meth:`_paginate` and :meth:`_fetch_page` provide a
  consistent interface for all paginated endpoints.
* **Bug fixes** — ``params["page:"]`` typo, ``print()`` → ``logger``, and the
  hardcoded ``"master"`` default branch is now a parameter.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from atlassian.bitbucket.cloud import Cloud

from bitbucket_mcp.config import BitbucketConfig
from bitbucket_mcp.credentials import mask_credentials

logger = logging.getLogger(__name__)

MAX_PAGE = 100  # Maximum number of pages to fetch for auto-paginated results


class BitbucketClient:
    """High-level client for the Bitbucket Cloud REST API."""

    def __init__(self, config: BitbucketConfig):
        """Initialize the Bitbucket client.

        Args:
            config: Bitbucket connection configuration.
        """
        self.config = config
        self._client = Cloud(
            url=config.url,
            username=config.app_username,
            password=config.app_password,
            backoff_and_retry=True,
        )
        self._workspace = self._client.workspaces.get(config.workspace)

    @classmethod
    def from_env(cls) -> BitbucketClient:
        """Create a client using environment variables."""
        return cls(BitbucketConfig.from_env())

    @property
    def client(self) -> Cloud:
        """Underlying atlassian-python-api Cloud instance."""
        return self._client

    @property
    def workspace(self):
        """Cached Bitbucket workspace object."""
        return self._workspace

    @property
    def workspace_name(self) -> str:
        return self.config.workspace

    def _fetch_page(
        self,
        endpoint: str,
        params: dict[str, Any],
        *,
        use_workspace: bool = False,
        advanced_mode: bool = False,
    ) -> Any:
        """Fetch a single page from a Bitbucket API endpoint.

        Args:
            endpoint: API endpoint path.
            params: Query parameters.
            use_workspace: If True, call ``workspace.get``; otherwise ``client.get``.
            advanced_mode: If True, return the raw response object.

        Returns:
            Parsed JSON dict (or raw response if *advanced_mode*).
        """
        caller = self.workspace if use_workspace else self.client
        return caller.get(endpoint, params=params, advanced_mode=advanced_mode)

    def _paginate(
        self,
        endpoint: str,
        params: dict[str, Any],
        *,
        use_workspace: bool = False,
        max_page: int = MAX_PAGE,
    ) -> list[dict[str, Any]]:
        """Auto-paginate across all pages of a Bitbucket API endpoint.

        Follows the ``next`` cursor in each response until exhausted or
        *max_page* is reached.

        Args:
            endpoint: API endpoint path.
            params: Query parameters (``page`` is managed automatically).
            use_workspace: If True, use ``workspace.get``; otherwise ``client.get``.
            max_page: Maximum number of pages to fetch.

        Returns:
            Aggregated list of ``values`` from every fetched page.
        """
        all_results: list[dict[str, Any]] = []
        page = params.get("page", 1)

        while True:
            params["page"] = page
            response = self._fetch_page(endpoint, params, use_workspace=use_workspace)

            if "values" in response:
                all_results.extend(response["values"])

            if response.get("next") is None:
                break

            page += 1
            if page > max_page:
                logger.warning("Reached maximum page limit of %s", max_page)
                break

        return all_results

    def code_search(self, search_query: str, page: int = 1, pagelen: int = 50) -> list[dict[str, Any]]:
        """Search code in the Bitbucket workspace.

        Credentials in the returned segments are masked automatically.

        Args:
            search_query: The search query string.
            page: Page number to fetch.
            pagelen: Number of items per page.

        Returns:
            List of code search result dicts.
        """
        params = {
            "search_query": search_query,
            "page": page,
            "pagelen": pagelen,
        }
        logger.info("Code search: %s (page %s)", search_query, page)
        response = self._fetch_page("/search/code", params, use_workspace=True)

        results = response.get("values", [])
        _mask_search_results(results)
        return results

    def get_repositories(
        self,
        search_query: Optional[str] = None,
        sort: Optional[str] = None,
        role: Optional[str] = None,
        page: int = 1,
        pagelen: int = 50,
    ) -> list[dict[str, Any]]:
        """List repositories in the workspace.

        Args:
            search_query: Optional query string to filter (e.g. ``name ~ "foo"``).
            sort: Optional sort parameter (e.g. ``-updated_on``).
            role: Optional role filter (e.g. ``admin``, ``contributor``).
            page: Page number to fetch.
            pagelen: Number of items per page.

        Returns:
            List of repository objects.
        """
        params: dict[str, Any] = {
            "pagelen": pagelen,
            "page": page,
        }  # BUGFIX: was "page:"
        params["q"] = search_query or ""
        if sort:
            params["sort"] = sort
        if role:
            params["role"] = role

        logger.info("Fetching repositories page %s", page)
        response = self._fetch_page(f"/repositories/{self.workspace_name}", params)
        return response.get("values", [])

    def create_branch(self, repo_slug: str, branch_name: str, target_hash: str = "master") -> dict[str, Any]:
        """Create a new branch in a repository.

        Args:
            repo_slug: The slug of the repository.
            branch_name: The name of the new branch.
            target_hash: The commit hash or branch name to branch from
                (defaults to ``"master"``).

        Returns:
            Dict with the created branch info on success, or an error dict.
        """
        result = self.client.post(
            f"/repositories/{self.workspace_name}/{repo_slug}/refs/branches",
            json={"name": branch_name, "target": {"hash": target_hash}},
            headers={"Accept": "application/json"},
            advanced_mode=True,
        )
        if result.status_code == 201:
            return result.json()
        logger.error("Failed to create branch: %s %s", result.status_code, result.text)
        return {
            "error": "Failed to create branch",
            "status_code": result.status_code,
            "message": result.text,
        }

    def get_commits(
        self,
        repo_slug: str,
        include: Optional[list[str]] = None,
        exclude: Optional[list[str]] = None,
        path: Optional[str] = None,
        max_page: int = MAX_PAGE,
    ) -> list[dict[str, Any]]:
        """Get commits for a repository, auto-paginating.

        Args:
            repo_slug: The slug of the repository.
            include: Optional list of refs to include.
            exclude: Optional list of refs to exclude.
            path: Optional file/directory path filter.
            max_page: Maximum number of pages to fetch.

        Returns:
            List of commit objects.
        """
        params: dict[str, Any] = {"pagelen": 50}

        if include:
            params["include"] = list(include)
        if exclude:
            params["exclude"] = list(exclude)
        if path:
            params["path"] = path

        logger.info("Fetching commits for repository %s", repo_slug)
        return self._paginate(
            f"/repositories/{self.workspace_name}/{repo_slug}/commits",
            params,
            max_page=max_page,
        )

    def get_pull_requests(
        self,
        repo_slug: str,
        state: Optional[str] = None,
        page: int = 1,
        pagelen: int = 50,
    ) -> list[dict[str, Any]]:
        """List pull requests for a repository.

        Args:
            repo_slug: The slug of the repository.
            state: Optional state filter (``OPEN``, ``MERGED``, ``DECLINED``).
            page: Page number.
            pagelen: Items per page.

        Returns:
            List of pull request objects.
        """
        params: dict[str, Any] = {"pagelen": pagelen, "page": page}
        if state:
            params["state"] = state

        logger.info("Fetching pull requests page %s for %s", page, repo_slug)
        response = self._fetch_page(
            f"/repositories/{self.workspace_name}/{repo_slug}/pullrequests",
            params,
        )
        return response.get("values", [])

    def get_pull_request(self, repo_slug: str, pull_request_id: int) -> dict[str, Any]:
        """Retrieve a single pull request by ID.

        Args:
            repo_slug: The slug of the repository.
            pull_request_id: The numeric ID of the pull request.

        Returns:
            Pull request object, or empty dict if not found.
        """
        logger.info("Fetching PR %s in %s", pull_request_id, repo_slug)
        response = self._fetch_page(
            f"/repositories/{self.workspace_name}/{repo_slug}/pullrequests/{pull_request_id}",
            {},
        )
        return response if response else {}

    def get_pull_request_diff(self, repo_slug: str, pull_request_id: int) -> str:
        """Get the diff for a pull request.

        The API returns a 302 redirect to the actual diff endpoint; the
        requests library follows redirects automatically.

        Args:
            repo_slug: The slug of the repository.
            pull_request_id: The numeric ID of the pull request.

        Returns:
            The diff as a string, or an error message.
        """
        logger.info("Fetching diff for PR %s in %s", pull_request_id, repo_slug)
        response = self._fetch_page(
            f"/repositories/{self.workspace_name}/{repo_slug}/pullrequests/{pull_request_id}/diff",
            {},
            advanced_mode=True,
        )
        if response and response.status_code == 200:
            return response.text
        status = response.status_code if response else "unknown"
        return f"Error retrieving diff: status code {status}"

    def get_pull_request_comments(
        self,
        repo_slug: str,
        pull_request_id: int,
        page: int = 1,
        pagelen: int = 50,
    ) -> list[dict[str, Any]]:
        """Get comments for a pull request.

        Args:
            repo_slug: The slug of the repository.
            pull_request_id: The numeric ID of the pull request.
            page: Page number.
            pagelen: Items per page.

        Returns:
            List of comment objects.
        """
        params: dict[str, Any] = {"pagelen": pagelen, "page": page}
        logger.info(
            "Fetching comments (page %s) for PR %s in %s",
            page,
            pull_request_id,
            repo_slug,
        )
        response = self._fetch_page(
            f"/repositories/{self.workspace_name}/{repo_slug}/pullrequests/{pull_request_id}/comments",
            params,
        )
        return response.get("values", [])

    def create_pull_request(
        self,
        repo_slug: str,
        branch_name: str,
        title: str,
        description: str,
        destination: str = "master",
    ) -> dict[str, Any]:
        """Create a pull request in a repository.

        Args:
            repo_slug: The slug of the repository.
            branch_name: The source branch name.
            title: The pull request title.
            description: The pull request description.
            destination: The destination branch (default ``"master"``).

        Returns:
            Dict with ``success`` bool and ``message`` / ``data``.
        """
        data = {
            "title": title,
            "source": {"branch": {"name": branch_name}},
            "destination": {"branch": {"name": destination}},
            "description": description,
        }
        result = self.client.post(
            f"/repositories/{self.workspace_name}/{repo_slug}/pullrequests",
            json=data,
            headers={"Accept": "application/json"},
            advanced_mode=True,
        )
        if result.status_code == 201:
            return {"success": True, "data": result.json()}
        # BUGFIX: was print() — now uses logger
        logger.error("Failed to create PR: %s %s", result.status_code, result.text)
        return {
            "success": False,
            "error": f"Failed to create PR (status {result.status_code}): {result.text}",
        }

    def get_file_content(self, repo_slug: str, commit: str, path: str) -> str:
        """Get the raw content of a file from a repository.

        Credentials are masked automatically (with full scan for YAML files).

        Args:
            repo_slug: The slug of the repository.
            commit: The commit hash or branch name.
            path: The path to the file within the repository.

        Returns:
            The raw file content as a string.

        Raises:
            Exception: If the API returns a non-200 status.
        """
        logger.info("Fetching file %s @ %s in %s", path, commit, repo_slug)
        response = self._fetch_page(
            f"/repositories/{self.workspace_name}/{repo_slug}/src/{commit}/{path}",
            {},
            advanced_mode=True,
        )
        if response.status_code == 200:
            content = response.text
            full_scan = path.endswith((".yaml", ".yml"))
            return mask_credentials(content, full_scan=full_scan)

        logger.error("Failed to fetch file content: %s", response.text)
        raise Exception(f"Failed to fetch file content: {response.status_code} - {response.text}")


_client: Optional[BitbucketClient] = None


def get_client() -> BitbucketClient:
    """Return a lazily-initialized shared :class:`BitbucketClient` instance.

    Creating a new ``Cloud`` connection on every tool call is wasteful (it
    re-authenticates and re-fetches workspace metadata).  This singleton keeps
    a single connection alive for the lifetime of the server process.
    """
    global _client
    if _client is None:
        _client = BitbucketClient.from_env()
    return _client


def reset_client() -> None:
    """Discard the cached client (useful for testing)."""
    global _client
    _client = None


def _mask_search_results(results: list[dict[str, Any]]) -> None:
    """Mask credentials in code search result segments (in-place)."""
    for result in results:
        if result.get("type") != "code_search_result":
            continue
        file_path = result.get("file", {}).get("path", "")
        full_scan = file_path.endswith((".yaml", ".yml"))
        for match in result.get("content_matches", []):
            for line_info in match.get("lines", []):
                for segment in line_info.get("segments", []):
                    if "text" in segment:
                        segment["text"] = mask_credentials(segment["text"], full_scan=full_scan)
