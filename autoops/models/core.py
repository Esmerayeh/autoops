"""Core SQLAlchemy models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON
from flask_login import UserMixin

from autoops.extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="viewer")
    failed_login_attempts = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime(timezone=True), nullable=True)
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)
    totp_secret = db.Column(db.String(64), nullable=True)
    is_totp_enabled = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat(),
        }


class MetricSnapshot(db.Model):
    __tablename__ = "metrics_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    captured_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    cpu_percent = db.Column(db.Float, nullable=False)
    memory_percent = db.Column(db.Float, nullable=False)
    disk_percent = db.Column(db.Float, nullable=False)
    swap_percent = db.Column(db.Float, nullable=False)
    network_bytes_sent = db.Column(db.BigInteger, nullable=False)
    network_bytes_recv = db.Column(db.BigInteger, nullable=False)
    disk_read_bytes = db.Column(db.BigInteger, nullable=False)
    disk_write_bytes = db.Column(db.BigInteger, nullable=False)
    uptime_seconds = db.Column(db.Float, nullable=False)
    load_average = db.Column(JSON, nullable=True)
    process_count = db.Column(db.Integer, nullable=False, default=0)
    anomaly_score = db.Column(db.Float, nullable=True)
    anomaly_flags = db.Column(JSON, nullable=True)
    raw_payload = db.Column(JSON, nullable=False)


class AlertEvent(db.Model):
    __tablename__ = "alert_events"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    alert_type = db.Column(db.String(60), nullable=False)
    metric_name = db.Column(db.String(40), nullable=False)
    severity = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    dedupe_key = db.Column(db.String(120), nullable=False, index=True)
    severity_score = db.Column(db.Float, nullable=False, default=0)
    probable_causes = db.Column(JSON, nullable=True)
    recommendation = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    raw_payload = db.Column(JSON, nullable=True)


class HealingAction(db.Model):
    __tablename__ = "healing_actions"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    policy_name = db.Column(db.String(120), nullable=False)
    action_type = db.Column(db.String(60), nullable=False)
    target = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(30), nullable=False)
    dry_run = db.Column(db.Boolean, nullable=False, default=True)
    escalation_level = db.Column(db.Integer, nullable=False, default=0)
    requires_confirmation = db.Column(db.Boolean, nullable=False, default=False)
    summary = db.Column(db.Text, nullable=False)
    rollback_notes = db.Column(db.Text, nullable=True)
    result_payload = db.Column(JSON, nullable=True)
    incident_id = db.Column(db.Integer, db.ForeignKey("incidents.id"), nullable=True)
    decision_confidence = db.Column(db.Float, nullable=True)
    safety_score = db.Column(db.Float, nullable=True)


class LoginAudit(db.Model):
    __tablename__ = "login_audit"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    username = db.Column(db.String(80), nullable=False)
    event_type = db.Column(db.String(30), nullable=False)
    success = db.Column(db.Boolean, nullable=False, default=False)
    ip_address = db.Column(db.String(80), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    details = db.Column(JSON, nullable=True)


class SystemRecommendation(db.Model):
    __tablename__ = "system_recommendations"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    summary = db.Column(db.String(255), nullable=False)
    reasoning = db.Column(db.Text, nullable=False)
    confidence = db.Column(db.Float, nullable=False, default=0)
    anomaly_score = db.Column(db.Float, nullable=False, default=0)
    probable_causes = db.Column(JSON, nullable=True)
    next_actions = db.Column(JSON, nullable=True)
    forecast = db.Column(JSON, nullable=True)
    mode = db.Column(db.String(20), nullable=False, default="rules")
    incident_id = db.Column(db.Integer, db.ForeignKey("incidents.id"), nullable=True)


class Incident(db.Model):
    __tablename__ = "incidents"

    id = db.Column(db.Integer, primary_key=True)
    incident_key = db.Column(db.String(120), nullable=False, unique=True, index=True)
    status = db.Column(db.String(20), nullable=False, default="detected")
    severity = db.Column(db.String(20), nullable=False, default="warning")
    title = db.Column(db.String(255), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    root_cause_hypothesis = db.Column(db.Text, nullable=True)
    correlation_score = db.Column(db.Float, nullable=False, default=0)
    opened_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    raw_payload = db.Column(JSON, nullable=True)


class IncidentEvent(db.Model):
    __tablename__ = "incident_events"

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey("incidents.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    event_type = db.Column(db.String(40), nullable=False)
    message = db.Column(db.Text, nullable=False)
    raw_payload = db.Column(JSON, nullable=True)


class FeedbackRecord(db.Model):
    __tablename__ = "feedback_records"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    incident_id = db.Column(db.Integer, db.ForeignKey("incidents.id"), nullable=True, index=True)
    healing_action_id = db.Column(db.Integer, db.ForeignKey("healing_actions.id"), nullable=True, index=True)
    metric_name = db.Column(db.String(40), nullable=True)
    process_name = db.Column(db.String(120), nullable=True)
    anomaly_was_real = db.Column(db.Boolean, nullable=True)
    action_effective = db.Column(db.Boolean, nullable=True)
    issue_reoccurred = db.Column(db.Boolean, nullable=True)
    confidence_before = db.Column(db.Float, nullable=True)
    confidence_after = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    raw_payload = db.Column(JSON, nullable=True)


class ClusterNode(db.Model):
    __tablename__ = "cluster_nodes"

    id = db.Column(db.Integer, primary_key=True)
    node_id = db.Column(db.String(120), nullable=False, unique=True, index=True)
    tenant_id = db.Column(db.String(80), nullable=False, default="default", index=True)
    cluster_name = db.Column(db.String(120), nullable=False, default="autoops-local-cluster", index=True)
    node_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(40), nullable=False, default="agent")
    environment = db.Column(db.String(40), nullable=False, default="development")
    region = db.Column(db.String(60), nullable=False, default="local")
    status = db.Column(db.String(30), nullable=False, default="online")
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    capabilities = db.Column(JSON, nullable=True)
    metadata_payload = db.Column(JSON, nullable=True)
    latest_metrics = db.Column(JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class ServiceDependency(db.Model):
    __tablename__ = "service_dependencies"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.String(80), nullable=False, default="default", index=True)
    cluster_name = db.Column(db.String(120), nullable=False, default="autoops-local-cluster", index=True)
    source = db.Column(db.String(120), nullable=False, index=True)
    target = db.Column(db.String(120), nullable=False, index=True)
    dependency_type = db.Column(db.String(40), nullable=False, default="internal")
    confidence = db.Column(db.Float, nullable=False, default=0.8)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    metadata_payload = db.Column(JSON, nullable=True)


class OrchestrationTask(db.Model):
    __tablename__ = "orchestration_tasks"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.String(80), nullable=False, default="default", index=True)
    cluster_name = db.Column(db.String(120), nullable=False, default="autoops-local-cluster", index=True)
    task_type = db.Column(db.String(80), nullable=False)
    target_node_id = db.Column(db.String(120), nullable=True, index=True)
    status = db.Column(db.String(30), nullable=False, default="queued", index=True)
    execution_mode = db.Column(db.String(30), nullable=False, default="simulated")
    payload = db.Column(JSON, nullable=True)
    result_payload = db.Column(JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
