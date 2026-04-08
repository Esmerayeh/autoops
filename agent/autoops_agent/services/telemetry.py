from datetime import UTC, datetime
import json
import uuid

from ..collectors.discovery import DiscoveryCollector
from ..collectors.host_metrics import HostMetricsCollector
from ..collectors.process_metrics import ProcessMetricsCollector
from ..collectors.service_health import ServiceHealthCollector
from ..core.http_client import ControlPlaneClient
from ..core.spool import get_spool
from .enrollment import EnrollmentService


class TelemetryService:
    def __init__(self) -> None:
        self.client = ControlPlaneClient()
        self.enrollment = EnrollmentService()
        self.spool = get_spool()
        self.collectors = [
            HostMetricsCollector(),
            ProcessMetricsCollector(),
            ServiceHealthCollector(),
            DiscoveryCollector(),
        ]

    def collect_and_flush(self) -> None:
        state = self.enrollment.ensure_registered()
        self.client.set_agent_token(state["agent_token"])

        events = []
        for collector in self.collectors:
            payload = collector.collect()
            if collector.name == "discovery":
                payload["node_id"] = state["node_id"]
            events.append(
                {
                    "event_type": collector.name,
                    "event_id": str(uuid.uuid4()),
                    "occurred_at": datetime.now(UTC).isoformat(),
                    "payload": payload,
                }
            )

        payload = {
            "batch_id": str(uuid.uuid4()),
            "sent_at": datetime.now(UTC).isoformat(),
            "events": events,
        }

        try:
            response = self.client.post("/telemetry/batches", payload, use_agent_token=True)
            response.raise_for_status()
            self._flush_spool()
        except Exception:
            self.spool.append("telemetry_batch", payload)

    def _flush_spool(self) -> None:
        rows = self.spool.fetch_batch(limit=25)
        if not rows:
            return
        ack_ids = []
        for row_id, event_type, raw_payload in rows:
            response = self.client.post("/telemetry/batches", json.loads(raw_payload), use_agent_token=True)
            if response.ok:
                ack_ids.append(row_id)
        self.spool.ack(ack_ids)
