"""Validation helpers for query parameters and forms."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ValidationResult:
    value: int
    valid: bool = True
    message: str | None = None


def clamp_int(raw: str | None, default: int, minimum: int, maximum: int) -> ValidationResult:
    try:
        value = int(raw or default)
    except (TypeError, ValueError):
        return ValidationResult(default, False, "Expected an integer value.")
    return ValidationResult(max(minimum, min(maximum, value)))
