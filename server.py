# server.py
import json
import logging
import os
from typing import Any, Dict, List

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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    mcp.run(transport="streamable-http")
