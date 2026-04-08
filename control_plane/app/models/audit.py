from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from control_plane.app.models.base import UUIDTenantBase


class AuditRecord(UUIDTenantBase):
    __tablename__ = "cp_audit_records"

    actor_type: Mapped[str] = mapped_column(String(32), index=True)
    actor_id: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    resource_type: Mapped[str] = mapped_column(String(120), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    outcome: Mapped[str] = mapped_column(String(32), index=True)
    details_json: Mapped[dict] = mapped_column(JSON, default=dict)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
