# Bitbucket MCP Server

This project provides an implementation of the Model Context Protocol (MCP) server in Python. It allows users to perform code searches across multiple pages of results and returns the search results in JSON format.

## Features

* Implements the MCP server protocol
* Searches code in Bitbucket using the Bitbucket API
* Supports searching across multiple pages of results
* Returns search results in JSON format
* Includes syntax rules for searching files in Bitbucket

## Requirements

* Python 3.x
* `atlassian-bitbucket-cloud` library
* `mcp` library
* `uv` for project management

## Configuration example

```json
"BitbucketMCP": {
      "type": "local",
      "command":[ "/Users/dmtr/.local/bin/uv",
        "run",
        "--with",
        "atlassian-python-api",
        "--with",
        "mcp[cli]",
        "mcp",
        "run",
        "/Users/dmtr/proj/python/bitbucket_mcp/server.py"
      ],
      "environment": {
        "BITBUCKET_WORKSPACE": "bmat-music",
        "APP_USERNAME": "username",
        "APP_PASSWORD": "password"
      }
      }
}
```



