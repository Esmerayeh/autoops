"""Consistent API response helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def success_response(data: dict[str, Any], meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "ok": True,
        "timestamp": utc_iso(),
        "data": data,
        "meta": meta or {},
    }


def error_response(code: str, message: str, status: int, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "timestamp": utc_iso(),
        "error": {
            "code": code,
            "message": message,
            "status": status,
            "details": details or {},
        },
    }
