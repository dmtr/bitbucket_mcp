"""Configuration for the Bitbucket MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BitbucketConfig:
    """Bitbucket connection configuration.

    Attributes:
        workspace: Name of the Bitbucket workspace.
        app_username: Bitbucket username / app key.
        app_password: Bitbucket app password.
        url: Bitbucket Cloud API URL.
    """

    workspace: str
    app_username: str
    app_password: str
    url: str = "https://api.bitbucket.org/"

    @classmethod
    def from_env(cls) -> BitbucketConfig:
        """Create a config from environment variables.

        Raises:
            ValueError: If any required environment variable is missing.
        """
        workspace = os.environ.get("BITBUCKET_WORKSPACE", "")
        username = os.environ.get("APP_USERNAME", "")
        password = os.environ.get("APP_PASSWORD", "")
        url = os.environ.get("BITBUCKET_URL", "https://api.bitbucket.org/")

        missing = [
            name
            for name, val in (
                ("BITBUCKET_WORKSPACE", workspace),
                ("APP_USERNAME", username),
                ("APP_PASSWORD", password),
            )
            if not val
        ]
        if missing:
            raise ValueError(
                "Missing required environment variables: " + ", ".join(missing)
            )

        return cls(
            workspace=workspace,
            app_username=username,
            app_password=password,
            url=url,
        )
