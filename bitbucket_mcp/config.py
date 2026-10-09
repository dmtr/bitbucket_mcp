"""Configuration for the Bitbucket MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BitbucketConfig:
    """Bitbucket connection configuration.

    Attributes:
        workspace: Name of the Bitbucket workspace.
        access_token: Bitbucket workspace access token.
        url: Bitbucket Cloud API URL.
    """

    workspace: str
    access_token: str
    url: str = "https://api.bitbucket.org/"

    @classmethod
    def from_env(cls) -> BitbucketConfig:
        """Create a config from environment variables.

        Raises:
            ValueError: If any required environment variable is missing.
        """
        workspace = os.environ.get("BITBUCKET_WORKSPACE", "")
        access_token = os.environ.get("BITBUCKET_ACCESS_TOKEN", "")
        url = os.environ.get("BITBUCKET_URL", "https://api.bitbucket.org/")

        missing = [
            name
            for name, val in (
                ("BITBUCKET_WORKSPACE", workspace),
                ("BITBUCKET_ACCESS_TOKEN", access_token),
            )
            if not val
        ]
        if missing:
            raise ValueError(
                "Missing required environment variables: " + ", ".join(missing)
            )

        return cls(
            workspace=workspace,
            access_token=access_token,
            url=url,
        )
