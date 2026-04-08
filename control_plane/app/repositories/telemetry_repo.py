from sqlalchemy.orm import Session

from control_plane.app.models.agent import Agent
from control_plane.app.models.telemetry import TelemetryBatch, TelemetryEvent


class TelemetryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_agent(self, tenant_id: str, agent_uid: str) -> Agent | None:
        return self.db.query(Agent).filter(Agent.agent_uid == agent_uid, Agent.tenant_id == tenant_id).first()

    def create_batch(self, batch: TelemetryBatch) -> TelemetryBatch:
        self.db.add(batch)
        self.db.flush()
        return batch

    def create_event(self, event: TelemetryEvent) -> TelemetryEvent:
        self.db.add(event)
        self.db.flush()
        return event
