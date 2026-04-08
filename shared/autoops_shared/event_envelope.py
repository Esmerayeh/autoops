from pydantic import BaseModel, Field


class EventSource(BaseModel):
    kind: str
    agent_id: str | None = None
    node_id: str | None = None
    actor_id: str | None = None


class EventEnvelope(BaseModel):
    event_id: str
    event_type: str
    tenant_id: str
    source: EventSource
    occurred_at: str
    schema_version: int = 1
    payload: dict = Field(default_factory=dict)
