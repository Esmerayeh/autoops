import uuid

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from control_plane.app.core.db import Base
from control_plane.app.models.base import UUIDTenantBase


class TelemetryBatch(UUIDTenantBase):
    __tablename__ = "cp_telemetry_batches"

    batch_id: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    agent_id: Mapped[str] = mapped_column(index=True)
    event_count: Mapped[int] = mapped_column(Integer, default=0)


class TelemetryEvent(Base):
    __tablename__ = "cp_telemetry_events"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(index=True)
    telemetry_batch_id: Mapped[str] = mapped_column(index=True)
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    occurred_at: Mapped[str] = mapped_column(String(40), index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
