"""Incident grouping and lifecycle tracking."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from autoops.extensions import db
from autoops.models import Incident, IncidentEvent


class IncidentService:
    """Groups repeated alerts into incidents and tracks their lifecycle."""

    def upsert_incidents(self, alerts: list[dict[str, Any]], analysis: dict[str, Any], snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        incidents: list[dict[str, Any]] = []
        for alert in alerts:
            incident_key = f"{alert['metric']}:{alert['severity']}"
            incident = Incident.query.filter(
                Incident.incident_key == incident_key,
                Incident.status != "resolved",
            ).first()
            if incident is None:
                incident = Incident(
                    incident_key=incident_key,
                    severity=alert["severity"],
                    title=alert["title"],
                    summary=alert["message"],
                    root_cause_hypothesis=" ".join(analysis.get("probable_causes", [])[:2]),
                    correlation_score=min(1.0, (alert["severity_score"] / 100) + analysis["anomaly"]["score"] * 0.4),
                    raw_payload={"alert": alert, "snapshot": snapshot["timestamp"]},
                )
                db.session.add(incident)
                db.session.flush()
                db.session.add(
                    IncidentEvent(
                        incident_id=incident.id,
                        event_type="detected",
                        message=alert["message"],
                        raw_payload=alert,
                    )
                )
            else:
                incident.updated_at = datetime.now(timezone.utc)
                incident.summary = alert["message"]
                incident.root_cause_hypothesis = " ".join(analysis.get("probable_causes", [])[:2])
            incidents.append(
                {
                    "id": incident.id,
                    "incident_key": incident.incident_key,
                    "status": incident.status,
                    "severity": incident.severity,
                    "title": incident.title,
                    "summary": incident.summary,
                    "root_cause_hypothesis": incident.root_cause_hypothesis,
                    "correlation_score": round(incident.correlation_score * 100, 2),
                }
            )
        db.session.commit()
        return incidents

    def resolve_if_recovered(self, current_incidents: list[dict[str, Any]], health_score: float) -> None:
        active_keys = {item["incident_key"] for item in current_incidents}
        open_incidents = Incident.query.filter(Incident.status != "resolved").all()
        for incident in open_incidents:
            if incident.incident_key in active_keys:
                continue
            if health_score >= 75:
                incident.status = "resolved"
                incident.resolved_at = datetime.now(timezone.utc)
                db.session.add(
                    IncidentEvent(
                        incident_id=incident.id,
                        event_type="resolved",
                        message="Incident auto-resolved after metrics stabilized.",
                    )
                )
        db.session.commit()
