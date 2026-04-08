from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from control_plane.app.models.base import UUIDTenantBase


class Alert(UUIDTenantBase):
    __tablename__ = "cp_alerts"

    node_id: Mapped[str | None] = mapped_column(index=True, nullable=True)
    service_id: Mapped[str | None] = mapped_column(index=True, nullable=True)
    dedupe_key: Mapped[str] = mapped_column(String(160), index=True)
    severity: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="open")
    details_json: Mapped[dict] = mapped_column(JSON, default=dict)
