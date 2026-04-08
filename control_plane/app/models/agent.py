from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from control_plane.app.models.base import UUIDTenantBase


class Agent(UUIDTenantBase):
    __tablename__ = "cp_agents"

    node_id: Mapped[str] = mapped_column(index=True)
    agent_uid: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    version: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    capabilities_json: Mapped[dict] = mapped_column(JSON, default=dict)
