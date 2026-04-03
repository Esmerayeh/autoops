"""Lightweight response schema helpers without external runtime dependency."""

from __future__ import annotations

from typing import Any


def validate_health_payload(payload: dict[str, Any]) -> dict[str, Any]:
    required = {
        "status": str,
        "service": str,
        "sampler_running": bool,
        "uptime_seconds": (int, float),
        "db": str,
    }
    for key, expected_type in required.items():
        if key not in payload:
            raise ValueError(f"Missing health payload field: {key}")
        if not isinstance(payload[key], expected_type):
            raise TypeError(f"Invalid health payload field type for {key}")
    return payload


def validate_autonomy_status(payload: dict[str, Any]) -> dict[str, Any]:
    required = {
        "mode": str,
        "max_actions_per_hour": int,
        "recent_autonomous_actions": int,
        "decision_confidence_threshold": (int, float),
        "decision_safety_threshold": (int, float),
        "feedback_summary": dict,
    }
    for key, expected_type in required.items():
        if key not in payload:
            raise ValueError(f"Missing autonomy payload field: {key}")
        if not isinstance(payload[key], expected_type):
            raise TypeError(f"Invalid autonomy payload field type for {key}")
    return payload


def validate_api_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    if "ok" not in payload or "timestamp" not in payload or "data" not in payload:
        raise ValueError("Invalid API envelope")
    return payload
