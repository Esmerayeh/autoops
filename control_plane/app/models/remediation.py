from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from control_plane.app.models.base import UUIDTenantBase


class RemediationAction(UUIDTenantBase):
    __tablename__ = "cp_remediation_actions"

    incident_id: Mapped[str | None] = mapped_column(index=True, nullable=True)
    target_node_id: Mapped[str | None] = mapped_column(index=True, nullable=True)
    policy_id: Mapped[str | None] = mapped_column(index=True, nullable=True)
    action_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="requested")
    approval_status: Mapped[str] = mapped_column(String(32), index=True, default="pending")
    request_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    result_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
