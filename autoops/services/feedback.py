"""Feedback learning and post-action evaluation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from flask import Flask

from autoops.extensions import db
from autoops.models import FeedbackRecord


class FeedbackLearningService:
    """Stores action outcomes and summarizes what has historically worked."""

    def __init__(self, app: Flask) -> None:
        self.app = app

    def effectiveness_summary(self) -> dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.app.config["FEEDBACK_LOOKBACK_DAYS"])
        records = FeedbackRecord.query.filter(FeedbackRecord.created_at >= cutoff).all()
        total = len(records)
        if not total:
            return {
                "total_records": 0,
                "action_success_rate": 0.5,
                "false_positive_rate": 0.1,
                "recurrence_rate": 0.1,
            }

        successes = sum(1 for record in records if record.action_effective is True)
        false_positives = sum(1 for record in records if record.anomaly_was_real is False)
        recurrences = sum(1 for record in records if record.issue_reoccurred is True)
        return {
            "total_records": total,
            "action_success_rate": round(successes / total, 3),
            "false_positive_rate": round(false_positives / total, 3),
            "recurrence_rate": round(recurrences / total, 3),
        }

    def record_feedback(
        self,
        *,
        incident_id: int | None,
        healing_action_id: int | None,
        metric_name: str | None,
        process_name: str | None,
        anomaly_was_real: bool | None,
        action_effective: bool | None,
        issue_reoccurred: bool | None,
        confidence_before: float | None,
        confidence_after: float | None,
        notes: str,
        raw_payload: dict[str, Any],
    ) -> FeedbackRecord:
        record = FeedbackRecord(
            incident_id=incident_id,
            healing_action_id=healing_action_id,
            metric_name=metric_name,
            process_name=process_name,
            anomaly_was_real=anomaly_was_real,
            action_effective=action_effective,
            issue_reoccurred=issue_reoccurred,
            confidence_before=confidence_before,
            confidence_after=confidence_after,
            notes=notes,
            raw_payload=raw_payload,
        )
        db.session.add(record)
        db.session.commit()
        return record
