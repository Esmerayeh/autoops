"""Security utility helpers."""

from __future__ import annotations

from collections.abc import Mapping

from flask import Response


def apply_security_headers(response: Response, config: Mapping[str, object]) -> None:
    """Apply baseline security headers to each response."""
    for key, value in config.get("SECURITY_HEADERS", {}).items():  # type: ignore[assignment]
        response.headers.setdefault(key, str(value))
