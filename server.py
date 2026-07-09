#!/usr/bin/env uv run
# /// script
# dependencies = ["atlassian-python-api", "mcp[cli]"]
# ///
#
# Backward-compatible entry point.
#
# This file used to contain the entire server.  The code now lives in the
# ``bitbucket_mcp`` package.  Existing configurations that reference
# ``server.py`` (e.g. ``uv run server.py``) will continue to work via this
# thin shim.

"""Shim that delegates to the :mod:`bitbucket_mcp` package."""

from bitbucket_mcp.__main__ import main

if __name__ == "__main__":
    main()
