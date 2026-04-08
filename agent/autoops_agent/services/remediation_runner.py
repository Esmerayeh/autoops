from ..core.http_client import ControlPlaneClient
from .enrollment import EnrollmentService


class RemediationRunnerService:
    """Poll remediation tasks, execute safe actions, and report results."""

    def __init__(self) -> None:
        self.client = ControlPlaneClient()
        self.enrollment = EnrollmentService()

    def poll_and_execute(self) -> None:
        state = self.enrollment.ensure_registered()
        self.client.set_agent_token(state["agent_token"])
        response = self.client.get(f"/remediation/agents/{state['agent_id']}/tasks", use_agent_token=True)
        response.raise_for_status()
        tasks = response.json().get("items", [])
        for task in tasks:
            result = self._execute(task)
            self.client.post(
                f"/remediation/actions/{task['action_id']}/result",
                result,
                use_agent_token=True,
            ).raise_for_status()

    def _execute(self, task: dict) -> dict:
        action_type = task["action_type"]
        request_payload = task.get("request_payload", {})
        if action_type == "collect_diagnostics":
            return {
                "success": True,
                "details": {
                    "performed": True,
                    "type": action_type,
                    "requested": request_payload,
                },
                "message": "Diagnostics bundle simulated",
            }
        if action_type in {"restart_service", "kill_process"}:
            return {
                "success": False,
                "details": {
                    "performed": False,
                    "type": action_type,
                    "requested": request_payload,
                    "mode": "safe-simulated",
                },
                "message": "Dangerous action blocked in MVP safe mode",
            }
        return {
            "success": False,
            "details": {"performed": False, "type": action_type},
            "message": "Unsupported remediation action",
        }
