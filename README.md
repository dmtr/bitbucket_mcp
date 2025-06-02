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

## Usage

1. Install the required libraries: `pip install atlassian-bitbucket-cloud mcp json logging`
2. Set the following environment variables:
	* `APP_USERNAME`: Your Bitbucket app username
	* `APP_PASSWORD`: Your Bitbucket app password
	* `BITBUCKET_WORKSPACE`: The name of your Bitbucket workspace
3. Run the tool: `mcp dev server.py`
