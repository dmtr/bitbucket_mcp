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

## Requirements

* Python 3.x
* `atlassian-python-api` library
* `mcp` library with CLI support
* `uv` for project management

## Environment Variables

The server requires the following environment variables:
* `BITBUCKET_WORKSPACE` - Your Bitbucket workspace name
* `APP_USERNAME` - Bitbucket username
* `APP_PASSWORD` - Bitbucket password or app password

## Configuration Example

```json
"BitbucketMCP": {
      "type": "local",
      "command":[ "uv",
        "run",
        "server.py"
      ],
      "environment": {
        "BITBUCKET_WORKSPACE": "test_workspace",
        "APP_USERNAME": "username",
        "APP_PASSWORD": "password"
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

