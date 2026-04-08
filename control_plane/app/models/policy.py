from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from control_plane.app.models.base import UUIDTenantBase


class Policy(UUIDTenantBase):
    __tablename__ = "cp_policies"

    name: Mapped[str] = mapped_column(String(120), index=True)
    policy_type: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    scope_json: Mapped[dict] = mapped_column(JSON, default=dict)
    rules_json: Mapped[dict] = mapped_column(JSON, default=dict)
    is_enabled: Mapped[bool] = mapped_column(default=True)
