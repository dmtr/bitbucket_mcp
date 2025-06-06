# server.py
import json
import logging
import os
from typing import Any, Dict, List, Optional

from atlassian.bitbucket.cloud import Cloud
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

SYNTAX_RULES = """Following are the syntax rules for searching files in Bitbucket:
A query in Bitbucket has to contain one search term.
Search operators are words that can be added to searches to help narrow down the results. Operators must be in ALL CAPS. These are the search operators that can be used to search for files:
AND
OR
NOT
-
(  )
Multiple terms can be used, and they form a boolean query that implicitly uses the AND operator. So a query for "bitbucket server" is equivalent to "bitbucket AND server".
Wildcard searches (e.g. qu?ck buil*) and regular expressions in queries are not supported.
Single characters within search terms are ignored as they’re not indexed by Bitbucket for performance reasons (e.g. searching for “foo a bar” is the same as searching for just “foo bar” as the character “a” in the search is ignored).
Case is not preserved, however search operators must be in ALL CAPS.
Queries cannot have more than 9 expressions (e.g. combinations of terms and operators).
To specify a programming language, use the `lang:` operator followed by the language name (e.g. `lang:python`), so if the query is "my_function lang:python", it will search for the term "def my_function" in Python files.
To specify a project use  project: operator followed by the project name (e.g. `project:my_project`), so if the query is "my_function project:my_project", it will search for the term "def my_function" in files of the specified project.
"""

APP_USERNAME = os.environ.get("APP_USERNAME", "")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")

MAX_PAGE = 100  # Maximum number of pages to fetch for search results


class BitbucketCodeSearch:
    def __init__(self, workspace_name: str, url: str = "https://api.bitbucket.org/", app_username: str = APP_USERNAME, app_password: str = APP_PASSWORD):
        """
        Initialize BitbucketCodeSearch client.

        Args:
            workspace_name: Name of the Bitbucket workspace
            url: Bitbucket API URL
            app_username: username
            app_password: password
        """

        self.workspace_name = workspace_name
        self.client = Cloud(
            url=url,
            username=app_username,
            password=app_password,
            backoff_and_retry=True,
        )
        self.workspace = self.client.workspaces.get(workspace_name)

    def _get_all_search_results(self, search_query: str, max_page: int = MAX_PAGE) -> List[dict]:
        """
        Fetch all search results across multiple pages.

        Args:
            search_query: The search query string

        Returns:
            List of all search result values
        """
        all_results = []
        page = 1

        while True:
            params = {"search_query": search_query}
            if page > 1:
                params["page"] = page

            logger.info("Fetching page %s", page)
            response = self.workspace.get("/search/code", params=params)

            if "values" in response:
                all_results.extend(response["values"])

            if response.get("next") is None:
                break

            page += 1
            if page > max_page:
                logger.warning("Reached maximum page limit of %s", max_page)
                break

        return all_results

    def get_raw_matches(self, search_query: str, max_page: int = MAX_PAGE) -> List[Dict[str, Any]]:
        """
        Get matches for the search query.

        Args:
            search_query: The search query string

        Returns:
            List of dictionaries:
            [
                {
                  "type": "code_search_result",
                  "content_match_count": 2,
                  "content_matches": [
                    {
                      "lines": [
                        {
                          "line": 2,
                          "segments": []
                        },
                        {
                          "line": 3,
                          "segments": [
                            {
                              "text": "def "
                            },
                            {
                              "text": "foo",
                              "match": true
                            },
                            {
                              "text": "():"
                            }
                          ]
                        },
                        {
                          "line": 4,
                          "segments": [
                            {
                              "text": "    print(\"snek\")"
                            }
                          ]
                        },
                        {
                          "line": 5,
                          "segments": []
                        }
                      ]
                    }
                  ],
                  "path_matches": [
                    {
                      "text": "src/"
                    },
                    {
                      "text": "foo",
                      "match": true
                    },
                    {
                      "text": ".py"
                    }
                  ],
                  "file": {
                    "path": "src/foo.py",
                    "type": "commit_file",
                    "links": {
                      "self": {
                        "href": "https://api.bitbucket.org/2.0/repositories/my-workspace/demo/src/ad6964b5fe2880dbd9ddcad1c89000f1dbcbc24b/src/foo.py"
                      }
                    }
                  }
                }
              ]

        """
        return self._get_all_search_results(search_query, max_page)

    def get_repositories_list(
        self, search_query: Optional[str] = None, sort: Optional[str] = None, role: Optional[str] = None, max_page: int = MAX_PAGE
    ) -> List[Dict[str, Any]]:
        """
        Search repositories in the workspace.

        Args:
            search_query: Optional query string to filter repositories (e.g., "name=foo")
            sort: Optional sort parameter (e.g., "name" or "-created_on")
            role: Optional filter by role (e.g., "admin", "contributor", "member")
            max_page: Maximum number of pages to fetch

        Returns:
            List of repository objects
        """
        all_results = []
        page = 1

        while True:
            params = {"pagelen": 50}
            params["q"] = search_query or ""
            if sort:
                params["sort"] = sort
            if role:
                params["role"] = role
            if page > 1:
                params["page"] = page

            logger.info("Fetching repositories page %s", page)
            response = self.client.get(
                f"/repositories/{self.workspace_name}",
                params=params,
            )

            if "values" in response:
                all_results.extend(response["values"])

            if response.get("next") is None:
                break

            page += 1
            if page > max_page:
                logger.warning("Reached maximum page limit of %s", max_page)
                break

        return all_results

    def create_branch(self, repo_slug: str, branch_name: str) -> str:
        """
        Create a new branch in the specified repository.

        Args:
            repo_slug: The slug of the repository where the branch will be created
        Returns:
            A string indicating the success or failure of the branch creation
            Response example:
            {
              "type": "<string>",
              "links": {
                "self": {
                  "href": "<string>",
                  "name": "<string>"
                },
                "commits": {
                  "href": "<string>",
                  "name": "<string>"
                },
                "html": {
                  "href": "<string>",
                  "name": "<string>"
                }
              },
              "name": "<string>",
              "target": {
                "type": "<string>"
              },
              "merge_strategies": [
                "merge_commit"
              ],
              "default_merge_strategy": "<string>"
            }
        """
        result = self.client.post(
            f"/repositories/{self.workspace_name}/{repo_slug}/refs/branches",
            json={"name": branch_name, "target": {"hash": "master"}},
            headers={
                "Accept": "application/json",
            },
            advanced_mode=True,
        )
        if result.status_code == 201:
            return json.dumps(result.json())
        else:
            return json.dumps({"error": "Failed to create branch", "status_code": result.status_code, "message": result.text})
            
    def get_commits(self, repo_slug: str, include: Optional[List[str]] = None, exclude: Optional[List[str]] = None, 
                    path: Optional[str] = None, max_page: int = MAX_PAGE) -> List[Dict[str, Any]]:
        """
        Get a list of commits for the specified repository.
        
        Args:
            repo_slug: The slug of the repository to get commits from
            include: Optional list of refs to include (e.g. ["master", "feature-branch"])
            exclude: Optional list of refs to exclude (e.g. ["dev"])
            path: Optional file or directory path to filter commits by
            max_page: Maximum number of pages to fetch
        Returns:
            List of commit objects
        """
        all_results = []
        page = 1
        
        while True:
            params = {"pagelen": 50}
            
            # Add include/exclude parameters if provided
            if include:
                for ref in include:
                    params.setdefault("include", []).append(ref)
            if exclude:
                for ref in exclude:
                    params.setdefault("exclude", []).append(ref)
            
            # Add path filter if provided
            if path:
                params["path"] = path
                
            if page > 1:
                params["page"] = page
                
            logger.info("Fetching commits page %s for repository %s", page, repo_slug)
            response = self.client.get(
                f"/repositories/{self.workspace_name}/{repo_slug}/commits",
                params=params,
            )
            
            if "values" in response:
                all_results.extend(response["values"])
                
            if response.get("next") is None:
                break
                
            page += 1
            if page > max_page:
                logger.warning("Reached maximum page limit of %s", max_page)
                break
                
        return all_results


mcp = FastMCP("BitbucketMCP")


@mcp.prompt()
def bitbucket_code_search_prompt() -> str:
    """
    Prompt for Bitbucket code search.

    Returns:
        A string containing the syntax rules for searching files in Bitbucket
    """
    return SYNTAX_RULES


@mcp.tool()
def bitbucket_code_search(
    search_query: str,
    max_page: int = MAX_PAGE,
) -> str:
    """
    Perform a code search in Bitbucket.

    Args:
        search_query: The search query string
        max_page: Maximum number of pages to fetch for search results
    Returns:
        A string representation of the search results in JSON format
    """
    bitbucket_tool = BitbucketCodeSearch(workspace_name=os.environ.get("BITBUCKET_WORKSPACE", ""))
    results = bitbucket_tool.get_raw_matches(search_query, max_page)

    if not results:
        return "No results found."

    return json.dumps(results)


@mcp.prompt()
def bitbucket_get_repositories_prompt() -> str:
    return """This tool allows you to search for repositories in a Bitbucket workspace.
           You can filter repositories by name, sort them, and specify roles. The results will be returned in JSON format.
           Response example:
           [
                {
                  "type": "<string>",
                  "links": {
                    "self": {
                      "href": "<string>",
                      "name": "<string>"
                    },
                    "html": {
                      "href": "<string>",
                      "name": "<string>"
                    },
                    "avatar": {
                      "href": "<string>",
                      "name": "<string>"
                    },
                    "pullrequests": {
                      "href": "<string>",
                      "name": "<string>"
                    },
                    "commits": {
                      "href": "<string>",
                      "name": "<string>"
                    },
                    "forks": {
                      "href": "<string>",
                      "name": "<string>"
                    },
                    "watchers": {
                      "href": "<string>",
                      "name": "<string>"
                    },
                    "downloads": {
                      "href": "<string>",
                      "name": "<string>"
                    },
                    "clone": [
                      {
                        "href": "<string>",
                        "name": "<string>"
                      }
                    ],
                    "hooks": {
                      "href": "<string>",
                      "name": "<string>"
                    }
                  },
                  "uuid": "<string>",
                  "full_name": "<string>",
                  "is_private": true,
                  "scm": "git",
                  "owner": {
                    "type": "<string>"
                  },
                  "name": "<string>",
                  "description": "<string>",
                  "created_on": "<string>",
                  "updated_on": "<string>",
                  "size": 2154,
                  "language": "<string>",
                  "has_issues": true,
                  "has_wiki": true,
                  "fork_policy": "allow_forks",
                  "project": {
                    "type": "<string>"
                  },
                  "mainbranch": {
                    "type": "<string>"
                  }
                }
              ]"""


@mcp.tool()
def bitbucket_get_repositories(
    search_query: Optional[str] = None,
    sort: Optional[str] = None,
    role: Optional[str] = None,
    max_page: int = MAX_PAGE,
) -> str:
    """
    Get list of repositories in a Bitbucket workspace.

    Args:
        search_query: Optional query string to filter repositories (e.g. 'name ~ "reportal-reports"')
        sort: Optional sort parameter (e.g., "-updated_on" or "-created_on")
        role: Optional filter by role (e.g., "admin", "contributor", "member")
        max_page: Maximum number of pages to fetch
    Returns:
        A string representation of the repositories in JSON format
    """
    bitbucket_tool = BitbucketCodeSearch(workspace_name=os.environ.get("BITBUCKET_WORKSPACE", ""))
    results = bitbucket_tool.get_repositories_list(search_query, sort, role, max_page)

    if not results:
        return "No repositories found."

    return json.dumps(results)


@mcp.tool()
def bitbucket_create_branch(repo_slug: str, branch_name: str) -> str:
    """
    Create a new branch in a Bitbucket repository.

    Args:
        repo_slug: The slug of the repository where the branch will be created
        branch_name: The name of the new branch to be created
    Returns:
        A string representation of the branch creation result in JSON format
    """
    bitbucket_tool = BitbucketCodeSearch(workspace_name=os.environ.get("BITBUCKET_WORKSPACE", ""))
    result = bitbucket_tool.create_branch(repo_slug, branch_name)
    return result


@mcp.prompt()
def bitbucket_get_commits_prompt() -> str:
    return """This tool allows you to retrieve a list of commits from a Bitbucket repository.
           You can filter commits by including or excluding specific refs, and by specifying a file or directory path.
           The results will be returned in JSON format.
           Response example:
           [
                {
                  "type": "commit",
                  "hash": "<string>",
                  "date": "<string>",
                  "author": {
                    "type": "author",
                    "raw": "<string>",
                    "user": {
                      "type": "user"
                    }
                  },
                  "message": "<string>",
                  "summary": {
                    "raw": "<string>",
                    "markup": "markdown",
                    "html": "<string>"
                  },
                  "parents": []
                }
           ]"""


@mcp.tool()
def bitbucket_get_commits(
    repo_slug: str,
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
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
    bitbucket_tool = BitbucketCodeSearch(workspace_name=os.environ.get("BITBUCKET_WORKSPACE", ""))
    results = bitbucket_tool.get_commits(repo_slug, include, exclude, path, max_page)

    if not results:
        return "No commits found."

    return json.dumps(results)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    mcp.run(transport="streamable-http")
