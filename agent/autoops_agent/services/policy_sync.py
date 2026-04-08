import json
from pathlib import Path
import time

from ..core.config import settings
from ..core.http_client import ControlPlaneClient
from .enrollment import EnrollmentService


POLICY_CACHE_PATH = Path(".agent-policies.json")


class PolicySyncService:
    def __init__(self) -> None:
        self.client = ControlPlaneClient()
        self.enrollment = EnrollmentService()
        self.last_refresh = 0.0

    def maybe_refresh(self) -> None:
        now = time.time()
        if now - self.last_refresh < settings.policy_refresh_seconds:
            return
        state = self.enrollment.ensure_registered()
        self.client.set_agent_token(state["agent_token"])
        response = self.client.get(f"/fleet/agents/{state['agent_id']}/policies", use_agent_token=True)
        if response.ok:
            POLICY_CACHE_PATH.write_text(json.dumps(response.json(), indent=2), encoding="utf-8")
            self.last_refresh = now
