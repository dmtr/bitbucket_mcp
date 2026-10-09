# Bitbucket MCP Server

This project provides an implementation of the Model Context Protocol (MCP) server in Python. It allows users to interact with Bitbucket repositories through a standardized interface, supporting code searches, repository management, and more.

## Features

* Implements the MCP server protocol for Bitbucket integration
* Searches code in Bitbucket repositories with support for multiple pages of results
* Retrieves repository information and commit history
* Fetches file contents from repositories
* Creates branches and pull requests
* Automatically masks sensitive credentials in search results
* Returns data in JSON format
* Includes syntax rules for searching files in Bitbucket

## Project Structure

```
bitbucket_mcp/
├── __init__.py          # Package init
├── __main__.py          # CLI entry point (argparse, logging, mcp.run)
├── server.py            # FastMCP instance + plugin-style tool/prompt registration
├── client.py            # BitbucketClient class (unified pagination, shared instance)
├── credentials.py       # mask_credentials() utility
├── config.py            # BitbucketConfig dataclass + env-var validation
└── prompts.py           # SYNTAX_RULES + TOOL_PROMPTS dictionary
```

### Adding a New Tool

1. **Add a method** to `BitbucketClient` in `client.py`.
2. **Add a tool function** in `server.py` using the `@bitbucket_tool` decorator — the function signature defines the MCP input schema, and the body delegates to the client via `_call()`.
3. **(Optional) Add a prompt** by adding an entry to `TOOL_PROMPTS` in `prompts.py` — it's auto-registered, no `@mcp.prompt()` boilerplate needed.

### Adding a New Prompt

Just add an entry to the `TOOL_PROMPTS` dict in `prompts.py`. The prompt is automatically registered as `{key}_prompt` at server startup.

## Requirements

* Python 3.11+
* `atlassian-python-api` library
* `mcp` library with CLI support
* `uv` for project management

## Environment Variables

The server requires the following environment variables:
* `BITBUCKET_WORKSPACE` - Your Bitbucket workspace name
* `BITBUCKET_ACCESS_TOKEN` - Bitbucket workspace access token
* `BITBUCKET_URL` - (Optional) Bitbucket API URL, defaults to `https://api.bitbucket.org/`

> **Note:** Bitbucket app passwords are deprecated. Use a [workspace access token](https://support.atlassian.com/bitbucket-cloud/docs/workspace-access-tokens/) (`BITBUCKET_ACCESS_TOKEN`) instead of `APP_USERNAME`/`APP_PASSWORD`.

## Configuration Example

```json
"BitbucketMCP": {
      "type": "local",
      "command": ["uv", "run", "bitbucket-mcp"],
      "environment": {
        "BITBUCKET_WORKSPACE": "test_workspace",
        "BITBUCKET_ACCESS_TOKEN": "access_token"
      }
}
```

Alternatively, you can still use the backward-compatible shim:

```json
"BitbucketMCP": {
      "type": "local",
      "command": ["uv", "run", "server.py"],
      "environment": {
        "BITBUCKET_WORKSPACE": "test_workspace",
        "BITBUCKET_ACCESS_TOKEN": "access_token"
      }
}
```

## Available Tools

* `bitbucket_code_search` - Search code in repositories
* `bitbucket_get_repositories` - List and filter repositories
* `bitbucket_create_branch` - Create a new branch
* `bitbucket_get_commits` - Retrieve commit history
* `bitbucket_get_file_content` - Get raw file content
* `bitbucket_create_pr` - Create pull requests
* `bitbucket_get_pull_requests` - List pull requests for a repository
* `bitbucket_get_pull_request` - Retrieve a single pull request by ID
* `bitbucket_get_pull_request_diff` - Get the diff for a pull request
* `bitbucket_get_pull_request_comments` - Get comments for a pull request
