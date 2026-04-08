from pydantic import BaseModel, Field


class TelemetryEventPayload(BaseModel):
    event_type: str
    event_id: str
    occurred_at: str
    payload: dict = Field(default_factory=dict)


class TelemetryBatchRequest(BaseModel):
    batch_id: str
    sent_at: str
    events: list[TelemetryEventPayload]


class TelemetryBatchResponse(BaseModel):
    accepted: bool
    ingest_id: str
