"""Central autonomous decision engine."""

from __future__ import annotations

from typing import Any

from flask import Flask

from autoops.services.settings import SettingsService


class DecisionEngine:
    """Turn analytics + incidents + feedback into an explainable action decision."""

    def __init__(self, app: Flask) -> None:
        self.app = app
        self.settings = SettingsService(app)

    def decide(
        self,
        *,
        analysis: dict[str, Any],
        incidents: list[dict[str, Any]],
        feedback_summary: dict[str, Any],
        snapshot: dict[str, Any],
        healing_candidates: list[dict[str, Any]],
        recent_action_count: int,
    ) -> dict[str, Any]:
        anomaly_score = float(analysis["anomaly"]["score"])
        risk_score = float(analysis["risk"]["score"]) / 100.0
        confidence = min(
            0.99,
            (analysis["anomaly"]["confidence"] * 0.45)
            + (min(1.0, len(incidents) * 0.15))
            + (feedback_summary["action_success_rate"] * 0.20)
            + ((1 - feedback_summary["false_positive_rate"]) * 0.20),
        )
        safety = max(
            0.0,
            1.0
            - (recent_action_count / max(1, self.app.config["MAX_AUTONOMOUS_ACTIONS_PER_HOUR"]))
            - feedback_summary["recurrence_rate"] * 0.2,
        )

        decision = "do_nothing"
        reasoning = "No meaningful autonomous action is needed."
        should_auto_heal = False

        if incidents and anomaly_score >= 0.45:
            decision = "alert_only"
            reasoning = "An incident is active, but confidence is not yet high enough for remediation."

        if incidents and healing_candidates and confidence >= self.app.config["DECISION_CONFIDENCE_THRESHOLD"]:
            decision = "recommend_action"
            reasoning = "An incident is active, past outcomes are reasonably strong, and a guarded remediation exists."

        autonomy_mode = self.settings.get_autonomy_mode()

        if (
            autonomy_mode == "autonomous"
            and incidents
            and healing_candidates
            and confidence >= self.app.config["DECISION_CONFIDENCE_THRESHOLD"]
            and safety >= self.app.config["DECISION_SAFETY_THRESHOLD"]
            and recent_action_count < self.app.config["MAX_AUTONOMOUS_ACTIONS_PER_HOUR"]
            and risk_score >= 0.55
        ):
            decision = "auto_heal"
            should_auto_heal = True
            reasoning = "Persistent risk is high, a safe policy exists, and recent feedback supports autonomous action."

        return {
            "decision": decision,
            "should_auto_heal": should_auto_heal,
            "confidence": round(confidence, 3),
            "safety_score": round(safety, 3),
            "risk_level": analysis["risk"]["label"],
            "why": reasoning,
            "recommended_action_type": healing_candidates[0]["action_type"] if healing_candidates else None,
            "mode": autonomy_mode,
        }
