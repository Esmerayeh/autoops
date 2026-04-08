import json
from pathlib import Path

from ..core.config import settings
from ..core.http_client import ControlPlaneClient


STATE_PATH = Path(".agent-state.json")


class EnrollmentService:
    def __init__(self) -> None:
        self.client = ControlPlaneClient()

    def ensure_registered(self) -> dict:
        state = self._load_state()
        if state.get("agent_id") and state.get("agent_token"):
            self.client.set_agent_token(state["agent_token"])
            return state

        response = self.client.post(
            "/fleet/agents/register",
            {
                "tenant_slug": settings.tenant_slug,
                "node_uid": settings.node_uid,
                "hostname": settings.hostname,
                "environment": settings.environment,
                "region": settings.region,
                "agent_version": settings.agent_version,
                "capabilities": {
                    "host_metrics": True,
                    "process_metrics": True,
                    "service_discovery": True,
                },
            },
        )
        response.raise_for_status()
        state = response.json()
        self.client.set_agent_token(state["agent_token"])
        STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
        return state

    def _load_state(self) -> dict:
        if not STATE_PATH.exists():
            return {}
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
