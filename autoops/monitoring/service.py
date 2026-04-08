"""System monitoring and sampling services."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import psutil
from flask import Flask

from autoops.analytics.engine import AnalyticsEngine
from autoops.analytics.adaptive import AdaptiveThresholdEngine
from autoops.extensions import db
from autoops.healing.engine import HealingEngine
from autoops.models import AlertEvent, FeedbackRecord, HealingAction, Incident, IncidentEvent, MetricSnapshot, SystemRecommendation
from autoops.services.decision_engine import DecisionEngine
from autoops.services.feedback import FeedbackLearningService
from autoops.services.incidents import IncidentService


class MonitoringService:
    """Coordinates metric collection, analysis, persistence, and caching."""

    def __init__(self, app: Flask) -> None:
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.lock = threading.RLock()
        self.history: deque[dict[str, Any]] = deque(maxlen=app.config["MAX_HISTORY_POINTS"])
        self.alert_cache: deque[dict[str, Any]] = deque(maxlen=300)
        self.action_cache: deque[dict[str, Any]] = deque(maxlen=300)
        self.request_latencies: deque[float] = deque(maxlen=500)
        self.api_cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self.persist_counter = 0
        self.last_sample_at: str | None = None
        self.started_at = time.time()
        self.last_action_summary = "No healing actions yet"
        self.analytics = AnalyticsEngine(app)
        self.adaptive = AdaptiveThresholdEngine()
        self.healing = HealingEngine(app)
        self.feedback = FeedbackLearningService(app)
        self.incidents = IncidentService()
        self.decision_engine = DecisionEngine(app)
        self.control_plane = None
        self.settings = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_network = psutil.net_io_counters()
        self._last_disk_io = psutil.disk_io_counters()
        self._pending_validations: deque[dict[str, Any]] = deque(maxlen=40)

    def start(self) -> None:
        """Start the background sampler thread."""
        if self._thread and self._thread.is_alive():
            return
        if self.app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="autoops-monitor")
        self._thread.start()

    def _run(self) -> None:
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            self.logger.exception("Failed to warm CPU sampler.")

        while not self._stop_event.is_set():
            loop_started = time.time()
            try:
                with self.app.app_context():
                    snapshot = self.collect_snapshot()
                    feedback_summary = self.feedback.effectiveness_summary()
                    adaptive_profile = self.adaptive.build_profile(list(self.history), snapshot)
                    analysis = self.analytics.analyze(snapshot, list(self.history), adaptive_profile, feedback_summary)
                    snapshot["analysis"] = analysis
                    self._record_snapshot(snapshot)
                    self._record_alerts(analysis)
                    incidents = self.incidents.upsert_incidents(analysis.get("alerts", []), analysis, snapshot)
                    decision = self.decision_engine.decide(
                        analysis=analysis,
                        incidents=incidents,
                        feedback_summary=feedback_summary,
                        snapshot=snapshot,
                        healing_candidates=self.healing.evaluate(snapshot, analysis),
                        recent_action_count=self._recent_autonomous_action_count(),
                    )
                    analysis["incidents"] = incidents
                    analysis["decision"] = decision
                    actions = self.healing.execute_candidates(
                        self.healing.evaluate(snapshot, analysis),
                        decision,
                        incident_id=incidents[0]["id"] if incidents else None,
                    )
                    self._record_actions(actions)
                    self._persist_if_needed(snapshot, analysis, actions)
                    if self.control_plane:
                        self.control_plane.update_local_node_snapshot(snapshot["metrics"])
                    self._queue_feedback_validation(snapshot, analysis, actions)
                    self._validate_previous_actions(snapshot)
                    self.incidents.resolve_if_recovered(incidents, self._health_score(snapshot, analysis))
                    self.prune_retention()
                    self.api_cache.clear()
            except Exception:
                self.logger.exception("Monitoring loop failed.")
            sleep_for = max(0.25, self.app.config["SAMPLE_INTERVAL_SECONDS"] - (time.time() - loop_started))
            time.sleep(sleep_for)

    def collect_snapshot(self) -> dict[str, Any]:
        """Collect a rich host snapshot with observability metadata."""
        now = datetime.now(timezone.utc)
        virtual_memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disk = psutil.disk_usage(os.path.abspath(os.sep))
        cpu_percent = psutil.cpu_percent(interval=None)
        network = psutil.net_io_counters()
        disk_io = psutil.disk_io_counters()
        boot_time = psutil.boot_time()
        load_average = None
        if hasattr(os, "getloadavg"):
            try:
                load_average = list(os.getloadavg())
            except OSError:
                load_average = None

        network_delta = {
            "bytes_sent_per_sec": max(0, network.bytes_sent - getattr(self._last_network, "bytes_sent", 0)),
            "bytes_recv_per_sec": max(0, network.bytes_recv - getattr(self._last_network, "bytes_recv", 0)),
        }
        disk_delta = {
            "read_bytes_per_sec": max(0, disk_io.read_bytes - getattr(self._last_disk_io, "read_bytes", 0)) if disk_io else 0,
            "write_bytes_per_sec": max(0, disk_io.write_bytes - getattr(self._last_disk_io, "write_bytes", 0)) if disk_io else 0,
        }
        self._last_network = network
        self._last_disk_io = disk_io

        snapshot = {
            "timestamp": now.isoformat().replace("+00:00", "Z"),
            "metrics": {
                "cpu": round(cpu_percent, 2),
                "cpu_per_core": [round(value, 2) for value in psutil.cpu_percent(interval=None, percpu=True)],
                "memory": round(virtual_memory.percent, 2),
                "disk": round(disk.percent, 2),
                "swap": round(swap.percent, 2),
                "network": {
                    "bytes_sent": int(network.bytes_sent),
                    "bytes_recv": int(network.bytes_recv),
                    **network_delta,
                },
                "disk_io": {
                    "read_bytes": int(disk_io.read_bytes) if disk_io else 0,
                    "write_bytes": int(disk_io.write_bytes) if disk_io else 0,
                    **disk_delta,
                },
                "uptime_seconds": round(time.time() - boot_time, 2),
                "load_average": load_average,
                "process_count": len(psutil.pids()),
                "api_latency_ms_p50": round(self.percentile_latency(50), 2),
                "api_latency_ms_p95": round(self.percentile_latency(95), 2),
            },
            "host": self.get_host_summary(),
            "processes": self.get_top_processes(limit=self.app.config["PROCESS_LIST_LIMIT"]),
        }
        self.last_sample_at = snapshot["timestamp"]
        return snapshot

    def _record_snapshot(self, snapshot: dict[str, Any]) -> None:
        with self.lock:
            self.history.append(snapshot)

    def _record_alerts(self, analysis: dict[str, Any]) -> None:
        alerts = analysis.get("alerts", [])
        if not alerts:
            return
        with self.lock:
            for alert in alerts:
                self.alert_cache.appendleft(alert)

    def _record_actions(self, actions: list[dict[str, Any]]) -> None:
        if not actions:
            return
        with self.lock:
            for action in actions:
                self.last_action_summary = action["summary"]
                self.action_cache.appendleft(action)

    def _persist_if_needed(self, snapshot: dict[str, Any], analysis: dict[str, Any], actions: list[dict[str, Any]]) -> None:
        self.persist_counter += 1
        if self.persist_counter % self.app.config["SNAPSHOT_PERSIST_EVERY"] != 0:
            return
        metric = snapshot["metrics"]
        record = MetricSnapshot(
            captured_at=datetime.fromisoformat(snapshot["timestamp"].replace("Z", "+00:00")),
            cpu_percent=metric["cpu"],
            memory_percent=metric["memory"],
            disk_percent=metric["disk"],
            swap_percent=metric["swap"],
            network_bytes_sent=metric["network"]["bytes_sent"],
            network_bytes_recv=metric["network"]["bytes_recv"],
            disk_read_bytes=metric["disk_io"]["read_bytes"],
            disk_write_bytes=metric["disk_io"]["write_bytes"],
            uptime_seconds=metric["uptime_seconds"],
            load_average=metric["load_average"],
            process_count=metric["process_count"],
            anomaly_score=analysis["anomaly"]["score"],
            anomaly_flags=analysis["anomaly"]["flags"],
            raw_payload=snapshot,
        )
        db.session.add(record)

        for alert in analysis.get("alerts", []):
            db.session.add(
                AlertEvent(
                    alert_type=alert["type"],
                    metric_name=alert["metric"],
                    severity=alert["severity"],
                    title=alert["title"],
                    message=alert["message"],
                    dedupe_key=alert["dedupe_key"],
                    severity_score=alert["severity_score"],
                    probable_causes=alert.get("probable_causes"),
                    recommendation=alert.get("recommendation"),
                    raw_payload=alert,
                )
            )

        action_records = []
        for action in actions:
            record = HealingAction(
                policy_name=action["policy_name"],
                action_type=action["action_type"],
                target=action.get("target"),
                status=action["status"],
                dry_run=action["dry_run"],
                escalation_level=action["escalation_level"],
                requires_confirmation=action["requires_confirmation"],
                summary=action["summary"],
                rollback_notes=action.get("rollback_notes"),
                incident_id=action.get("incident_id"),
                decision_confidence=action.get("decision_confidence"),
                safety_score=action.get("safety_score"),
                result_payload=action,
            )
            db.session.add(record)
            action_records.append((action, record))

        recommendation = analysis.get("recommendation")
        if recommendation:
            db.session.add(
                SystemRecommendation(
                    summary=recommendation["summary"],
                    reasoning=recommendation["reasoning"],
                    confidence=recommendation["confidence"],
                    anomaly_score=recommendation["anomaly_score"],
                    probable_causes=recommendation["probable_causes"],
                    next_actions=recommendation["next_actions"],
                    forecast=recommendation["forecast"],
                    mode=recommendation["mode"],
                    incident_id=analysis.get("incidents", [{}])[0].get("id") if analysis.get("incidents") else None,
                )
            )

        db.session.commit()
        for action, record in action_records:
            action["id"] = record.id
            action["validation_status"] = "pending"

    def prune_retention(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.app.config["DATA_RETENTION_HOURS"])
        MetricSnapshot.query.filter(MetricSnapshot.captured_at < cutoff).delete()
        AlertEvent.query.filter(AlertEvent.created_at < cutoff).delete()
        HealingAction.query.filter(HealingAction.created_at < cutoff).delete()
        SystemRecommendation.query.filter(SystemRecommendation.created_at < cutoff).delete()
        Incident.query.filter(Incident.updated_at < cutoff, Incident.status == "resolved").delete()
        FeedbackRecord.query.filter(FeedbackRecord.created_at < cutoff).delete()
        db.session.commit()

    def record_request_latency(self, latency_ms: float, status_code: int) -> None:
        with self.lock:
            self.request_latencies.append(latency_ms)

    def percentile_latency(self, percentile: int) -> float:
        with self.lock:
            if not self.request_latencies:
                return 0.0
            values = sorted(self.request_latencies)
        index = min(len(values) - 1, max(0, int((percentile / 100) * (len(values) - 1))))
        return values[index]

    def get_cached(self, key: str, loader: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        with self.lock:
            cached = self.api_cache.get(key)
        if cached and time.time() - cached[0] <= self.app.config["API_CACHE_TTL_SECONDS"]:
            return cached[1]
        value = loader()
        with self.lock:
            self.api_cache[key] = (time.time(), value)
        return value

    def get_host_summary(self) -> dict[str, Any]:
        return {
            "hostname": os.getenv("COMPUTERNAME") or os.getenv("HOSTNAME") or "localhost",
            "platform": os.name,
            "cpu_count": psutil.cpu_count(logical=True),
            "physical_cpu_count": psutil.cpu_count(logical=False),
            "boot_time": datetime.fromtimestamp(psutil.boot_time(), tz=timezone.utc).isoformat().replace("+00:00", "Z"),
            "python_pid": os.getpid(),
            "environment": self.app.config["ENV_NAME"],
            "sampler_state": "running" if self._thread and self._thread.is_alive() else "stopped",
            "self_healing_mode": "active" if self.app.config["ENABLE_SELF_HEALING"] and not self.app.config["HEALING_DRY_RUN"] else "dry-run",
            "ml_mode": self.analytics.mode,
        }

    def get_top_processes(self, limit: int) -> list[dict[str, Any]]:
        processes = []
        attrs = ["pid", "name", "cpu_percent", "memory_percent", "status", "create_time", "username"]
        for proc in psutil.process_iter(attrs=attrs):
            try:
                info = proc.info
                processes.append(
                    {
                        "pid": info.get("pid"),
                        "name": info.get("name"),
                        "cpu_percent": round(info.get("cpu_percent", 0.0), 2),
                        "memory_percent": round(info.get("memory_percent", 0.0), 2),
                        "anomaly_score": round(min(100.0, (info.get("cpu_percent", 0.0) * 0.7) + (info.get("memory_percent", 0.0) * 0.3)), 2),
                        "status": info.get("status"),
                        "create_time": datetime.fromtimestamp(info["create_time"], tz=timezone.utc).isoformat().replace("+00:00", "Z")
                        if info.get("create_time")
                        else None,
                        "username": info.get("username"),
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        processes.sort(key=lambda item: item["cpu_percent"], reverse=True)
        return processes[:limit]

    def get_live_summary(self) -> dict[str, Any]:
        def loader() -> dict[str, Any]:
            with self.lock:
                latest = self.history[-1] if self.history else None
                recent_actions = list(self.action_cache)[:12]
            if not latest:
                latest = self.collect_snapshot()
                latest["analysis"] = self.analytics.analyze(latest, [], self.adaptive.build_profile([], latest), self.feedback.effectiveness_summary())
            analysis = latest["analysis"]
            health_score = self._health_score(latest, analysis)
            return {
                "snapshot": latest,
                "analysis": analysis,
                "recent_actions": recent_actions,
                "health_score": health_score,
                "cluster": self.control_plane.get_cluster_overview() if self.control_plane else None,
                "status_bar": {
                    "environment": self.app.config["ENV_NAME"],
                    "sampler_state": "running" if self._thread and self._thread.is_alive() else "stopped",
                    "self_healing_mode": "active" if self.app.config["ENABLE_SELF_HEALING"] and not self.app.config["HEALING_DRY_RUN"] else "dry-run",
                    "last_action": self.last_action_summary,
                    "autonomy_mode": self.settings.get_autonomy_mode() if self.settings else self.app.config["AUTONOMY_MODE"],
                },
            }

        return self.get_cached("live_summary", loader)

    def get_history(self, limit: int) -> list[dict[str, Any]]:
        with self.lock:
            return list(self.history)[-limit:]

    def get_alerts(self, limit: int) -> list[dict[str, Any]]:
        with self.lock:
            return list(self.alert_cache)[:limit]

    def get_incidents(self, limit: int) -> list[dict[str, Any]]:
        incidents = Incident.query.order_by(Incident.updated_at.desc()).limit(limit).all()
        return [
            {
                "id": item.id,
                "incident_key": item.incident_key,
                "severity": item.severity,
                "status": item.status,
                "title": item.title,
                "summary": item.summary,
                "root_cause_hypothesis": item.root_cause_hypothesis,
                "correlation_score": round(item.correlation_score * 100, 2),
                "opened_at": item.opened_at.isoformat().replace("+00:00", "Z"),
                "updated_at": item.updated_at.isoformat().replace("+00:00", "Z"),
                "resolved_at": item.resolved_at.isoformat().replace("+00:00", "Z") if item.resolved_at else None,
            }
            for item in incidents
        ]

    def get_actions(self, limit: int) -> list[dict[str, Any]]:
        with self.lock:
            return list(self.action_cache)[:limit]

    def get_recent_decisions(self, limit: int) -> list[dict[str, Any]]:
        decisions = []
        for item in self.get_history(limit):
            analysis = item.get("analysis", {})
            decision = analysis.get("decision")
            if not decision:
                continue
            decisions.append(
                {
                    "timestamp": item.get("timestamp"),
                    "incident_id": analysis.get("incidents", [{}])[0].get("id") if analysis.get("incidents") else None,
                    "decision": decision.get("decision"),
                    "confidence": decision.get("confidence"),
                    "safety_score": decision.get("safety_score"),
                    "risk_level": decision.get("risk_level"),
                    "why": decision.get("why"),
                    "chosen_action": decision.get("recommended_action_type"),
                    "mode": decision.get("mode"),
                }
            )
        return list(reversed(decisions))[-limit:]

    def get_feedback(self, limit: int) -> dict[str, Any]:
        records = FeedbackRecord.query.order_by(FeedbackRecord.created_at.desc()).limit(limit).all()
        return {
            "summary": self.feedback.effectiveness_summary(),
            "records": [
                {
                    "id": item.id,
                    "created_at": item.created_at.isoformat().replace("+00:00", "Z"),
                    "incident_id": item.incident_id,
                    "healing_action_id": item.healing_action_id,
                    "metric_name": item.metric_name,
                    "process_name": item.process_name,
                    "anomaly_was_real": item.anomaly_was_real,
                    "action_effective": item.action_effective,
                    "issue_reoccurred": item.issue_reoccurred,
                    "confidence_before": item.confidence_before,
                    "confidence_after": item.confidence_after,
                    "notes": item.notes,
                }
                for item in records
            ],
        }

    def get_autonomy_status(self) -> dict[str, Any]:
        live = self.get_live_summary()
        return {
            "mode": self.settings.get_autonomy_mode() if self.settings else self.app.config["AUTONOMY_MODE"],
            "max_actions_per_hour": self.app.config["MAX_AUTONOMOUS_ACTIONS_PER_HOUR"],
            "recent_autonomous_actions": self._recent_autonomous_action_count(),
            "decision_confidence_threshold": self.app.config["DECISION_CONFIDENCE_THRESHOLD"],
            "decision_safety_threshold": self.app.config["DECISION_SAFETY_THRESHOLD"],
            "latest_decision": live["analysis"].get("decision"),
            "feedback_summary": self.feedback.effectiveness_summary(),
        }

    def get_action_validation(self, action_id: int) -> dict[str, Any] | None:
        record = FeedbackRecord.query.filter_by(healing_action_id=action_id).order_by(FeedbackRecord.created_at.desc()).first()
        if not record:
            return None
        return {
            "action_id": action_id,
            "validation_status": "passed" if record.action_effective else "failed",
            "confidence_shift": round((record.confidence_after or 0) - (record.confidence_before or 0), 3),
            "before": (record.raw_payload or {}).get("before", {}),
            "after": (record.raw_payload or {}).get("after", {}),
            "notes": record.notes,
            "created_at": record.created_at.isoformat().replace("+00:00", "Z"),
        }

    def get_incident_timeline(self, limit: int) -> list[dict[str, Any]]:
        events = IncidentEvent.query.order_by(IncidentEvent.created_at.desc()).limit(limit).all()
        return [
            {
                "incident_id": event.incident_id,
                "timestamp": event.created_at.isoformat().replace("+00:00", "Z"),
                "event_type": event.event_type,
                "message": event.message,
            }
            for event in events
        ]

    def get_logs(self, level: str | None, limit: int) -> list[dict[str, Any]]:
        path = self.app.config["LOG_FILE"]
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()[-limit:]
        entries = []
        for raw in lines:
            raw = raw.rstrip("\n")
            entry = {
                "timestamp": None,
                "level": "INFO",
                "message": raw,
                "raw": raw,
            }
            if raw.startswith("{"):
                try:
                    parsed = json.loads(raw)
                    entry = {
                        "timestamp": parsed.get("timestamp"),
                        "level": parsed.get("level", "INFO"),
                        "message": parsed.get("message", ""),
                        "raw": raw,
                    }
                except Exception:
                    pass
            else:
                parts = raw.split(" ", 3)
                if len(parts) >= 4 and parts[2].startswith("["):
                    entry["timestamp"] = f"{parts[0]} {parts[1]}"
                    entry["level"] = parts[2].strip("[]")
                    entry["message"] = parts[3]
            if level and entry["level"].upper() != level.upper():
                continue
            entries.append(entry)
        return entries

    def health_payload(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "autoops-ai",
            "sampler_running": bool(self._thread and self._thread.is_alive()),
            "last_sample_at": self.last_sample_at,
            "uptime_seconds": round(time.time() - self.started_at, 2),
            "db": "ok",
        }

    def _health_score(self, snapshot: dict[str, Any], analysis: dict[str, Any]) -> float:
        return max(
            0,
            round(
                100
                - (snapshot["metrics"]["cpu"] * 0.25)
                - (snapshot["metrics"]["memory"] * 0.2)
                - (snapshot["metrics"]["disk"] * 0.15)
                - (analysis["anomaly"]["score"] * 25)
                - (analysis["risk"]["score"] * 0.15),
                1,
            ),
        )

    def _recent_autonomous_action_count(self) -> int:
        one_hour_ago = time.time() - 3600
        with self.lock:
            return sum(1 for action in self.action_cache if action.get("timestamp", 0) >= one_hour_ago and action.get("status") in {"completed", "simulated", "recommended"})

    def _queue_feedback_validation(self, snapshot: dict[str, Any], analysis: dict[str, Any], actions: list[dict[str, Any]]) -> None:
        for action in actions:
            if action.get("status") not in {"completed", "simulated", "recommended"}:
                continue
            self._pending_validations.append(
                {
                    "queued_at": time.time(),
                    "snapshot_before": snapshot["metrics"],
                    "action": action,
                    "analysis": analysis,
                }
            )

    def _validate_previous_actions(self, snapshot: dict[str, Any]) -> None:
        ready = []
        still_pending = deque(maxlen=self._pending_validations.maxlen)
        for item in self._pending_validations:
            if time.time() - item["queued_at"] >= max(5.0, self.app.config["SAMPLE_INTERVAL_SECONDS"] * 2):
                ready.append(item)
            else:
                still_pending.append(item)
        self._pending_validations = still_pending

        for item in ready:
            before = item["snapshot_before"]
            after = snapshot["metrics"]
            metric_name = item["action"]["action_type"].split("_")[0] if item["action"].get("action_type") else "cpu"
            improved = (after.get("cpu", 0) + after.get("memory", 0)) < (before.get("cpu", 0) + before.get("memory", 0))
            self.feedback.record_feedback(
                incident_id=item["action"].get("incident_id"),
                metric_name=metric_name,
                process_name=(item["action"].get("target") or "").split(":")[0] or None,
                anomaly_was_real=True,
                action_effective=improved,
                issue_reoccurred=not improved and snapshot["analysis"]["risk"]["score"] > 55 if snapshot.get("analysis") else None,
                healing_action_id=item["action"].get("id"),
                confidence_before=item["action"].get("decision_confidence"),
                confidence_after=min(0.99, (item["action"].get("decision_confidence") or 0.5) + (0.08 if improved else -0.1)),
                notes="Post-action validation from next telemetry window.",
                raw_payload={"before": before, "after": after, "action": item["action"]},
            )
            item["action"]["validation_status"] = "passed" if improved else "failed"
