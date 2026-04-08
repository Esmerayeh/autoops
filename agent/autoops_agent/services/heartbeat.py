from ..collectors.host_metrics import HostMetricsCollector
from ..core.http_client import ControlPlaneClient
from .enrollment import EnrollmentService


class HeartbeatService:
    def __init__(self) -> None:
        self.client = ControlPlaneClient()
        self.enrollment = EnrollmentService()
        self.collector = HostMetricsCollector()

    def send(self) -> None:
        state = self.enrollment.ensure_registered()
        self.client.set_agent_token(state["agent_token"])
        response = self.client.post(
            f"/fleet/agents/{state['agent_id']}/heartbeat",
            {
                "status": "healthy",
                "metrics": self.collector.collect(),
                "service_states": [],
            },
            use_agent_token=True,
        )
        response.raise_for_status()
