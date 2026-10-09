"""Prompt definitions for Bitbucket MCP tools.

Each entry in :data:`TOOL_PROMPTS` is automatically registered as an MCP prompt
when the server starts (see :mod:`bitbucket_mcp.server`).  Adding a new prompt
here is the only change needed — no separate ``@mcp.prompt()`` function required.
"""

from __future__ import annotations

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
Single characters within search terms are ignored as they're not indexed by Bitbucket for performance reasons (e.g. searching for "foo a bar" is the same as searching for just "foo bar" as the character "a" in the search is ignored).
Case is not preserved, however search operators must be in ALL CAPS.
Queries cannot have more than 9 expressions (e.g. combinations of terms and operators).
To specify a programming language, use the `lang:` operator followed by the language name (e.g. `lang:python`), so if the query is "my_function lang:python", it will search for the term "def my_function" in Python files.
Bitbucket can group repositories by projects. To specify a project use project: operator followed by the project name (e.g. `project:my_project`), so if the query is "my_function project:my_project", it will search for the term "def my_function" in files of the specified project.
"""


TOOL_PROMPTS: dict[str, str] = {
    "bitbucket_code_search": SYNTAX_RULES,
    "bitbucket_get_repositories": """This tool allows you to search for repositories in a Bitbucket workspace.
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
   ]""",
    "bitbucket_get_commits": """This tool allows you to retrieve a list of commits from a Bitbucket repository.
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
]""",
    "bitbucket_get_file_content": """This tool allows you to retrieve the raw content of a file from a Bitbucket repository.
You need to provide the repository slug, commit or branch name, and the file path.
The tool will return the raw content of the file as a string.""",
    "bitbucket_create_pr": """This tool allows you to create a pull request in a Bitbucket repository.
You need to provide the repository slug, branch name, title, description, and optionally the destination branch.
The tool will return a message indicating the success or failure of the pull request creation.""",
    "bitbucket_get_pull_requests": """This tool allows you to list pull requests for a Bitbucket repository.
You can optionally filter by state (e.g., OPEN, MERGED, DECLINED).
The tool returns a JSON list of pull request objects.""",
    "bitbucket_get_pull_request": """This tool retrieves a single pull request by its numeric ID.
Provide the repository slug and pull request ID. Returns a JSON object.
""",
    "bitbucket_get_pull_request_diff": """This tool retrieves the diff for a pull request by its numeric ID.
Provide the repository slug and pull request ID. Returns the diff as plain text.
Lock files are excluded by default and the output is capped at `max_chars`; use `paths`
to fetch specific files. Notes at the end ("[bitbucket-mcp] ...") list every file left out.
""",
    "bitbucket_get_pull_request_diffstat": """This tool lists the files changed by a pull request.
Provide the repository slug and pull request ID. Returns JSON with totals and, per file,
its path, status (added, removed, modified, renamed, ...) and lines added/removed.
Use it before fetching the diff of a large pull request.
""",
    "bitbucket_get_pull_request_comments": """This tool retrieves comments for a pull request by its numeric ID.
Provide the repository slug and pull request ID. Returns a JSON list of comment objects.
Each comment includes fields like id, user, content, created_on, updated_on, etc.
""",
}
