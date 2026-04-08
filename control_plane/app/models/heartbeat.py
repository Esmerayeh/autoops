from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from control_plane.app.models.base import UUIDTenantBase


class AgentHeartbeat(UUIDTenantBase):
    __tablename__ = "cp_agent_heartbeats"

    agent_id: Mapped[str] = mapped_column(index=True)
    node_id: Mapped[str] = mapped_column(index=True)
    received_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), index=True)
    health_status: Mapped[str] = mapped_column(String(32), index=True)
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)
