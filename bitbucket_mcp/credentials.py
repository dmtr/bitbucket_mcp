"""Credential masking utilities.

Masks sensitive data (API keys, tokens, passwords, connection strings, UUIDs)
in text returned from the Bitbucket API before exposing it to the LLM consumer.
"""

from __future__ import annotations

import re


def _yaml_and_python_patterns() -> list[str]:
    """Build regex patterns for YAML and Python-style key/value assignments.

    Matches keys like ``api_key``, ``api-key``, ``apiKey`` (case-insensitive via
    the ``\\b`` word boundary) followed by ``:`` or ``=`` and a quoted value.
    """
    sensitive_keys = [
        "api[_-]?key",
        "api[_-]?secret",
        "api[_-]?token",
        "access[_-]?token",
        "auth[_-]?token",
        "password",
        "secret[_-]?key",
        "credentials",
        "audience",
    ]
    # YAML: key: "value"   |   Python: key = "value"
    return [
        rf'(\b{key}\b[_\-\s]?[:=]\s*["\'])([^"\']+)(["\'])' for key in sensitive_keys
    ] + [rf'(\b{key}\b[_\-\s]?\s*=\s*["\'])([^"\']+)(["\'])' for key in sensitive_keys]


def mask_credentials(text: str, full_scan: bool = True) -> str:
    """Mask sensitive credentials in a string.

    Identifies and masks:
    - MongoDB connection strings
    - API keys / tokens / secrets in YAML or Python assignment syntax
    - JWT tokens
    - ``user:password@host`` credential patterns
    - UUIDs
    - Azure B2C login URLs
    - Long high-entropy strings (when *full_scan* is True)

    Args:
        text: The string that might contain credentials.
        full_scan: If True, additionally mask long alphanumeric strings
            (16+ chars). Enable for YAML/config files.

    Returns:
        The string with credentials replaced by ``********``.
    """

    # MongoDB connection strings: mongodb://user:password@host/db
    text = re.sub(r"(mongodb://[^:]+:)([^@]+)(@[^/\s]+)", r"\1********\3", text)

    # YAML / Python key-value patterns
    for pattern in _yaml_and_python_patterns():
        text = re.sub(pattern, r"\1********\3", text)

    # JWT tokens (three base64 segments separated by dots)
    text = re.sub(
        r"(eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,})",
        r"********",
        text,
    )

    # user:password@domain  (also covers amqp://, http://, etc.)
    text = re.sub(
        r"(?:(?:[a-zA-Z]+://)?([A-Za-z0-9\-]+:[A-Za-z0-9\-]+@[A-Za-z0-9\-\.]+(?:/[A-Za-z0-9\-]+)*))",
        r"********",
        text,
    )

    # UUIDs
    text = re.sub(
        r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
        r"********",
        text,
        flags=re.IGNORECASE,
    )

    # Azure B2C login URLs
    text = re.sub(
        r'([^\s"\']*b2clogin[^\s"\']*)', r"********", text, flags=re.IGNORECASE
    )

    if not full_scan:
        return text

    # Long high-entropy strings (passwords, API keys, etc.)
    text = re.sub(
        r"(?<![:/\w])([A-Za-z0-9+/~\.\-_]{16,})(?![:/\w])",
        "********",
        text,
    )

    # AWS-style keys (20+ alphanumeric chars)
    text = re.sub(
        r"(?<![:/\w])([A-Za-z0-9+/]{20,})(?![:/\w])",
        "********",
        text,
    )

    return text
