"""CLI entry point for the Bitbucket MCP server.

Run with::

    python -m bitbucket_mcp            # stdio (default)
    python -m bitbucket_mcp --transport sse
    uv run bitbucket-mcp               # via console-script entry point
"""

from __future__ import annotations

import argparse
import logging

from bitbucket_mcp.server import mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Bitbucket MCP server")
    parser.add_argument(
        "--transport",
        type=str,
        default="sse",
        choices=["streamable-http", "sse", "stdio"],
        help="Transport method for the server",
    )
    parser.add_argument(
        "--log_level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
