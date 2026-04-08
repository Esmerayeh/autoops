from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from control_plane.app.models.base import UUIDTenantBase


class Node(UUIDTenantBase):
    __tablename__ = "cp_nodes"

    node_uid: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    hostname: Mapped[str] = mapped_column(String(255), index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    environment: Mapped[str] = mapped_column(String(32), index=True)
    region: Mapped[str] = mapped_column(String(64), index=True)
    node_group: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="unknown", index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
