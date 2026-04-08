from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from control_plane.app.models.base import UUIDTenantBase


class Incident(UUIDTenantBase):
    __tablename__ = "cp_incidents"

    incident_key: Mapped[str] = mapped_column(String(160), index=True)
    severity: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="open")
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text)
    root_cause_json: Mapped[dict] = mapped_column(JSON, default=dict)
    affected_nodes_json: Mapped[list] = mapped_column(JSON, default=list)
