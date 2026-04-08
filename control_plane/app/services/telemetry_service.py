import uuid

from sqlalchemy.orm import Session

from control_plane.app.messaging.publishers import EventPublisher
from control_plane.app.models.telemetry import TelemetryBatch, TelemetryEvent
from control_plane.app.repositories.telemetry_repo import TelemetryRepository


class TelemetryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.publisher = EventPublisher()
        self.telemetry_repo = TelemetryRepository(db)

    def ingest_batch(self, tenant_id: str, agent_uid: str, payload: dict) -> dict:
        agent = self.telemetry_repo.get_agent(tenant_id, agent_uid)
        if not agent:
            raise ValueError("Unknown agent")

        batch = TelemetryBatch(
            tenant_id=tenant_id,
            agent_id=agent.id,
            batch_id=payload["batch_id"],
            event_count=len(payload.get("events", [])),
        )
        self.telemetry_repo.create_batch(batch)

        for event in payload.get("events", []):
            telemetry_event = TelemetryEvent(
                tenant_id=tenant_id,
                telemetry_batch_id=batch.id,
                event_type=event["event_type"],
                occurred_at=event["occurred_at"],
                payload_json=event.get("payload", {}),
            )
            self.telemetry_repo.create_event(telemetry_event)
            self.publisher.publish_telemetry(
                tenant_id=tenant_id,
                agent_uid=agent_uid,
                event_type=event["event_type"],
                payload=event.get("payload", {}),
                event_id=event["event_id"],
                occurred_at=event["occurred_at"],
            )

        self.db.commit()
        return {"accepted": True, "ingest_id": str(uuid.uuid4())}
