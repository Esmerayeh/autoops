"""Pydantic response schemas for high-value API contracts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ApiMeta(BaseModel):
    count: int | None = None
    level: str | None = None


class ApiEnvelope(BaseModel):
    ok: bool = True
    timestamp: str
    data: dict[str, Any]
    meta: dict[str, Any] = Field(default_factory=dict)


class HealthPayload(BaseModel):
    status: str
    service: str
    sampler_running: bool
    last_sample_at: str | None
    uptime_seconds: float
    db: str


class AutonomyStatusPayload(BaseModel):
    mode: str
    max_actions_per_hour: int
    recent_autonomous_actions: int
    decision_confidence_threshold: float
    decision_safety_threshold: float
    latest_decision: dict[str, Any] | None = None
    feedback_summary: dict[str, Any]
