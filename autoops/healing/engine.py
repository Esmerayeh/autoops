"""Policy-driven healing engine with safety guardrails."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from flask import Flask


class HealingEngine:
    """Evaluate configured policies and produce safe remediation actions."""

    def __init__(self, app: Flask) -> None:
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.policy_file = Path(app.config["HEALING_POLICY_FILE"])
        self.last_action_at = 0.0

    def policies(self) -> list[dict[str, Any]]:
        if not self.policy_file.exists():
            return []
        with open(self.policy_file, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def evaluate(self, snapshot: dict[str, Any], analysis: dict[str, Any]) -> list[dict[str, Any]]:
        metrics = snapshot["metrics"]
        actions: list[dict[str, Any]] = []
        for policy in self.policies():
            if metrics.get(policy["metric"], 0) < policy["threshold"]:
                continue
            action = self._apply_policy(policy, snapshot, analysis)
            if action:
                actions.append(action)
        return actions

    def execute_candidates(
        self,
        candidates: list[dict[str, Any]],
        decision: dict[str, Any],
        incident_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Convert candidate actions into final executed or recommended actions."""
        if not candidates:
            return []
        executed = []
        for action in candidates:
            final_action = dict(action)
            final_action["incident_id"] = incident_id
            final_action["decision_confidence"] = decision["confidence"]
            final_action["safety_score"] = decision["safety_score"]
            if decision["decision"] == "recommend_action":
                final_action["status"] = "recommended"
                final_action["summary"] = f"AI recommends: {final_action['summary']}"
            elif decision["decision"] == "alert_only":
                final_action["status"] = "alert_only"
                final_action["summary"] = f"Alert only: {final_action['summary']}"
            elif decision["decision"] == "do_nothing":
                continue
            executed.append(final_action)
            if decision["decision"] != "auto_heal":
                break
        return executed

    def _apply_policy(self, policy: dict[str, Any], snapshot: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any] | None:
        now = time.time()
        cooldown = self.app.config["HEALING_COOLDOWN_SECONDS"]
        if now - self.last_action_at < cooldown:
            return self._build_action(
                policy,
                "rate_limited",
                "Healing skipped because cooldown is active.",
                target=None,
                result_payload={"cooldown_seconds": cooldown},
            )

        action_type = policy["action_type"]
        requires_confirmation = bool(policy.get("requires_confirmation", False) and self.app.config["OPERATOR_CONFIRMATION_REQUIRED"])
        dry_run = bool(self.app.config["HEALING_DRY_RUN"] or not self.app.config["ENABLE_SELF_HEALING"])

        if action_type == "kill_process":
            top_process = snapshot.get("processes", [{}])[0]
            if not top_process:
                return None
            target_name = (top_process.get("name") or "").lower()
            target_pid = top_process.get("pid")
            if self._is_protected(target_pid, target_name):
                return self._build_action(
                    policy,
                    "blocked",
                    f"Skipped termination for protected process {target_name or 'unknown'} ({target_pid}).",
                    target=f"{target_name}:{target_pid}",
                )
            if requires_confirmation:
                return self._build_action(
                    policy,
                    "awaiting_confirmation",
                    f"Operator confirmation required before killing {target_name} ({target_pid}).",
                    target=f"{target_name}:{target_pid}",
                    requires_confirmation=True,
                )
            if dry_run:
                self.last_action_at = now
                return self._build_action(
                    policy,
                    "simulated",
                    f"Dry-run: would terminate process {target_name} ({target_pid}) due to sustained CPU pressure.",
                    target=f"{target_name}:{target_pid}",
                    result_payload={"mode": "simulation"},
                    rollback_notes="No rollback needed because no action was executed.",
                )
            result = self._kill_process(int(target_pid))
            self.last_action_at = now
            return self._build_action(
                policy,
                "completed" if result["ok"] else "failed",
                result["message"],
                target=f"{target_name}:{target_pid}",
                result_payload=result,
                rollback_notes="Restart the service manually if the process was business-critical.",
            )

        if action_type == "clear_temp":
            temp_path = Path(self.app.config["SAFE_TEMP_PATH"])
            if requires_confirmation:
                return self._build_action(
                    policy,
                    "awaiting_confirmation",
                    f"Operator confirmation required before cleaning {temp_path}.",
                    target=str(temp_path),
                    requires_confirmation=True,
                )
            if dry_run:
                self.last_action_at = now
                return self._build_action(
                    policy,
                    "simulated",
                    f"Dry-run: would clear safe temp/cache content under {temp_path}.",
                    target=str(temp_path),
                    rollback_notes="No rollback needed because this was a simulation.",
                )
            temp_path.mkdir(parents=True, exist_ok=True)
            removed = 0
            for item in temp_path.iterdir():
                if item.is_file():
                    item.unlink(missing_ok=True)
                    removed += 1
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                    removed += 1
            self.last_action_at = now
            return self._build_action(
                policy,
                "completed",
                f"Cleared {removed} temp/cache item(s) under {temp_path}.",
                target=str(temp_path),
                rollback_notes="Restore temp/cache artifacts only if application startup depends on them.",
            )

        if action_type == "recommend_manual_action":
            self.last_action_at = now
            summary = analysis["recommendation"]["next_actions"][0]
            return self._build_action(policy, "recommendation_only", summary, target=None)

        if action_type == "webhook_trigger":
            if not self.app.config["ALLOW_WEBHOOKS"] or not self.app.config["EXTERNAL_WEBHOOK_URL"]:
                return self._build_action(
                    policy,
                    "blocked",
                    "Webhook action blocked because external automation is disabled.",
                    target=None,
                )
            self.last_action_at = now
            return self._build_action(
                policy,
                "simulated" if dry_run else "completed",
                "Webhook trigger prepared for external remediation.",
                result_payload={"url": self.app.config["EXTERNAL_WEBHOOK_URL"]},
            )

        return self._build_action(policy, "ignored", f"No executor implemented for {action_type}.", target=None)

    def _kill_process(self, pid: int) -> dict[str, Any]:
        try:
            cmd = ["taskkill", "/PID", str(pid), "/F"] if os.name == "nt" else ["kill", "-9", str(pid)]
            completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if completed.returncode == 0:
                return {"ok": True, "message": f"Terminated process {pid} using {' '.join(cmd)}."}
            details = (completed.stderr or completed.stdout or "").strip()
            return {"ok": False, "message": f"Failed to terminate process {pid}: {details or 'unknown error'}."}
        except Exception as exc:
            self.logger.exception("Process termination failed.")
            return {"ok": False, "message": f"Termination error for process {pid}: {exc}"}

    def _build_action(
        self,
        policy: dict[str, Any],
        status: str,
        summary: str,
        target: str | None,
        requires_confirmation: bool | None = None,
        result_payload: dict[str, Any] | None = None,
        rollback_notes: str | None = None,
    ) -> dict[str, Any]:
        return {
            "timestamp": time.time(),
            "policy_name": policy["name"],
            "action_type": policy["action_type"],
            "status": status,
            "target": target,
            "dry_run": bool(self.app.config["HEALING_DRY_RUN"] or not self.app.config["ENABLE_SELF_HEALING"]),
            "escalation_level": int(policy.get("escalation_level", 0)),
            "requires_confirmation": bool(requires_confirmation if requires_confirmation is not None else policy.get("requires_confirmation", False)),
            "summary": summary,
            "rollback_notes": rollback_notes,
            "result_payload": result_payload or {},
        }

    def _is_protected(self, pid: int | None, name: str | None) -> bool:
        if pid in self.app.config["HEALING_PROTECTED_PIDS"]:
            return True
        if not name:
            return True
        if self.app.config["HEALING_ALLOWLIST"] and name not in self.app.config["HEALING_ALLOWLIST"]:
            return True
        return name in self.app.config["HEALING_BLOCKLIST"]
