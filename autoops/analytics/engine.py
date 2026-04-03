"""Explainable analytics engine with rule-based and optional ML modes."""

from __future__ import annotations

from statistics import mean
from typing import Any

from flask import Flask

try:
    from sklearn.ensemble import IsolationForest  # type: ignore
except Exception:  # pragma: no cover
    IsolationForest = None


class AnalyticsEngine:
    """Generate anomaly signals, forecasts, and recommendations."""

    def __init__(self, app: Flask) -> None:
        self.app = app
        self.mode = "ml" if IsolationForest else "rules"
        self._model = IsolationForest(random_state=42, contamination=0.15) if IsolationForest else None

    def analyze(
        self,
        snapshot: dict[str, Any],
        history: list[dict[str, Any]],
        adaptive_profile: dict[str, Any] | None = None,
        feedback_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metrics = snapshot["metrics"]
        alerts = self._build_alerts(metrics, history, adaptive_profile)
        anomaly = self._anomaly(metrics, history)
        trend = self._trend(history)
        forecast = self._forecast(history, metrics)
        causes = self._probable_causes(metrics, trend, alerts, snapshot)
        recommendation = self._recommendation(anomaly, trend, forecast, causes, alerts, feedback_summary or {})
        return {
            "mode": self.mode,
            "alerts": alerts,
            "anomaly": anomaly,
            "trend": trend,
            "forecast": forecast,
            "risk": self._risk(anomaly, alerts, forecast),
            "adaptive_profile": adaptive_profile or {},
            "probable_causes": causes,
            "recommendation": recommendation,
        }

    def _build_alerts(
        self,
        metrics: dict[str, Any],
        history: list[dict[str, Any]],
        adaptive_profile: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        thresholds = adaptive_profile.get("thresholds", {}) if adaptive_profile else {}
        recent = history[-self.app.config["SUSTAINED_BREACH_WINDOW"] :]
        for metric_name in ("cpu", "memory", "disk", "swap"):
            dynamic = thresholds.get(metric_name, {})
            warning = dynamic.get("warning", self.app.config["WARNING_THRESHOLD"])
            critical = dynamic.get("critical", self.app.config["CRITICAL_THRESHOLD"])
            value = metrics.get(metric_name, 0)
            severity = None
            if value >= critical:
                severity = "critical"
            elif value >= warning:
                severity = "warning"
            if not severity:
                continue
            sustained = sum(1 for item in recent if item.get("metrics", {}).get(metric_name, 0) >= warning)
            alerts.append(
                {
                    "type": "threshold_breach",
                    "metric": metric_name,
                    "severity": severity,
                    "title": f"{metric_name.upper()} {severity.title()} Alert",
                    "message": f"{metric_name.upper()} is at {value:.1f}% across a rolling window with {sustained} elevated samples.",
                    "dedupe_key": f"{metric_name}:{severity}:{int(value // 5)}",
                    "severity_score": round(min(100.0, value + sustained * 4), 2),
                    "recommendation": f"Investigate {metric_name} pressure against its learned baseline and correlate with process spikes.",
                }
            )
        deduped: dict[str, dict[str, Any]] = {}
        for alert in alerts:
            deduped[alert["dedupe_key"]] = alert
        return list(deduped.values())

    def _anomaly(self, metrics: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
        points = [
            [item["metrics"]["cpu"], item["metrics"]["memory"], item["metrics"]["disk"], item["metrics"]["swap"]]
            for item in history[-30:]
            if "metrics" in item
        ]
        current = [[metrics["cpu"], metrics["memory"], metrics["disk"], metrics["swap"]]]
        if self._model and len(points) >= 10:
            model = self._model.fit(points)
            score = float(abs(model.decision_function(current)[0]))
            prediction = int(model.predict(current)[0])
            flags = ["ml_detected_outlier" if prediction == -1 else "within_expected_range"]
            return {
                "score": round(score, 3),
                "confidence": round(min(0.98, 0.6 + min(score, 1.0) * 0.25), 2),
                "flags": flags,
                "source": "isolation_forest",
            }

        score = round(min(1.0, max(metrics["cpu"], metrics["memory"], metrics["disk"]) / 100), 3)
        flags = []
        if metrics["cpu"] > self.app.config["CRITICAL_THRESHOLD"]:
            flags.append("cpu_hot")
        if metrics["memory"] > self.app.config["CRITICAL_THRESHOLD"]:
            flags.append("memory_hot")
        if not flags:
            flags.append("stable")
        return {"score": score, "confidence": 0.74 if flags != ["stable"] else 0.92, "flags": flags, "source": "rules"}

    def _trend(self, history: list[dict[str, Any]]) -> dict[str, str]:
        trend: dict[str, str] = {}
        for metric_name in ("cpu", "memory", "disk", "swap"):
            values = [item["metrics"][metric_name] for item in history[-10:] if "metrics" in item]
            if len(values) < 2:
                trend[metric_name] = "steady"
                continue
            if values[-1] - values[0] > 8:
                trend[metric_name] = "rising"
            elif values[0] - values[-1] > 8:
                trend[metric_name] = "cooling"
            else:
                trend[metric_name] = "steady"
        return trend

    def _forecast(self, history: list[dict[str, Any]], metrics: dict[str, Any]) -> dict[str, Any]:
        forecast: dict[str, Any] = {}
        for metric_name in ("cpu", "memory"):
            values = [item["metrics"][metric_name] for item in history[-12:] if "metrics" in item]
            if not values:
                forecast[metric_name] = {"next_5m_estimate": metrics[metric_name], "method": "instant"}
                continue
            window = values[-5:] if len(values) >= 5 else values
            momentum = 0 if len(window) < 2 else (window[-1] - window[0]) / max(1, len(window) - 1)
            forecast[metric_name] = {
                "next_5m_estimate": round(max(0.0, min(100.0, mean(window) + momentum * 5)), 2),
                "method": "moving_average_plus_momentum",
            }
        return forecast

    def _probable_causes(
        self,
        metrics: dict[str, Any],
        trend: dict[str, str],
        alerts: list[dict[str, Any]],
        snapshot: dict[str, Any],
    ) -> list[str]:
        causes = []
        hot_process = next(iter(snapshot.get("processes", [])), None)
        if metrics["cpu"] > self.app.config["WARNING_THRESHOLD"]:
            suffix = f" Top suspect: {hot_process.get('name')} ({hot_process.get('pid')})." if hot_process else ""
            causes.append(f"A hot process or burst workload is likely driving CPU pressure.{suffix}")
        if metrics["memory"] > self.app.config["WARNING_THRESHOLD"]:
            causes.append("Memory-heavy process mix or leak-like behavior may be building.")
        if trend.get("disk") == "rising":
            causes.append("Disk saturation is trending upward; check logs, caches, and write-heavy jobs.")
        if metrics["swap"] > 35:
            causes.append("Swap pressure suggests memory exhaustion and possible latency spikes.")
        if not causes and alerts:
            causes.append("Correlated threshold signals exist without a single dominant resource.")
        if not causes:
            causes.append("No dominant issue detected in the current window.")
        return causes

    def _recommendation(
        self,
        anomaly: dict[str, Any],
        trend: dict[str, str],
        forecast: dict[str, Any],
        causes: list[str],
        alerts: list[dict[str, Any]],
        feedback_summary: dict[str, Any],
    ) -> dict[str, Any]:
        next_actions = []
        if any(alert["metric"] == "cpu" for alert in alerts):
            next_actions.append("Inspect the top CPU-consuming process before applying remediation.")
        if any(alert["metric"] == "memory" for alert in alerts):
            next_actions.append("Review worker memory growth and recycle unhealthy processes.")
        if any(alert["metric"] == "disk" for alert in alerts):
            next_actions.append("Prune temporary data and validate retention settings.")
        if not next_actions:
            next_actions.append("Continue monitoring and compare the next 5-minute forecast before intervening.")

        summary = "System stable with low intervention urgency."
        if alerts:
            summary = f"{len(alerts)} active alert signal(s) need attention."
        if anomaly["score"] > 0.7:
            summary = "Anomalous resource behavior detected; proactive action recommended."

        reasoning = " ".join(causes)
        if any(value == "rising" for value in trend.values()):
            reasoning += " At least one key resource is trending upward."
        if feedback_summary:
            reasoning += (
                f" Historical action success is {int(feedback_summary.get('action_success_rate', 0) * 100)}%"
                f" with false positives around {int(feedback_summary.get('false_positive_rate', 0) * 100)}%."
            )

        return {
            "summary": summary,
            "reasoning": reasoning,
            "confidence": anomaly["confidence"],
            "anomaly_score": anomaly["score"],
            "probable_causes": causes,
            "next_actions": next_actions,
            "forecast": forecast,
            "mode": self.mode,
        }

    def _risk(self, anomaly: dict[str, Any], alerts: list[dict[str, Any]], forecast: dict[str, Any]) -> dict[str, Any]:
        forecast_pressure = max(
            forecast.get("cpu", {}).get("next_5m_estimate", 0),
            forecast.get("memory", {}).get("next_5m_estimate", 0),
        )
        score = round(min(100.0, (anomaly["score"] * 55) + (len(alerts) * 10) + (forecast_pressure * 0.25)), 2)
        label = "low"
        if score >= 75:
            label = "high"
        elif score >= 45:
            label = "elevated"
        return {
            "score": score,
            "label": label,
            "early_warning": score >= 60,
        }
