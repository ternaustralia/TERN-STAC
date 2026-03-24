"""Shared auth-related helpers for data access operations."""

from __future__ import annotations

import warnings


def is_http_401_error(exc: Exception) -> bool:
    """Best-effort detection for unauthorized HTTP responses."""

    text = str(exc).lower()
    return (
        "http response code: 401" in text
        or ("401" in text and ("http" in text or "unauthorized" in text))
    )


def warn_auth_required(*, context: str = "") -> None:
    """Emit a user-facing warning about missing API key/auth setup."""

    prefix = f"{context}: " if context else ""
    warnings.warn(
        f"{prefix}Authentication is required before reading asset data. "
        "Configure API key access first. See https://github.com/ternaustralia/TERN-STAC",
        UserWarning,
        stacklevel=2,
    )
