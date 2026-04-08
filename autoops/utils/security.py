"""Security utility helpers."""

from __future__ import annotations

from collections.abc import Mapping
from functools import wraps
from urllib.parse import urlparse

from flask import Response, abort, request
from flask_login import current_user


def apply_security_headers(response: Response, config: Mapping[str, object]) -> None:
    """Apply baseline security headers to each response."""
    for key, value in config.get("SECURITY_HEADERS", {}).items():  # type: ignore[assignment]
        response.headers.setdefault(key, str(value))


def is_safe_next_url(target: str | None) -> bool:
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(target)
    return (not test_url.netloc or test_url.netloc == ref_url.netloc) and (not test_url.scheme or test_url.scheme in {"http", "https"})


def require_role(*roles: str):
    """Require an authenticated user to hold one of the supplied roles."""

    normalized = {role.lower() for role in roles}

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if str(getattr(current_user, "role", "")).lower() not in normalized:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator
