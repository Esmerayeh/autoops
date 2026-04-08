import uuid

from sqlalchemy import JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from control_plane.app.core.db import Base


class Role(Base):
    __tablename__ = "cp_roles"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_cp_role_name"),)

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(80), index=True)
    permissions: Mapped[dict] = mapped_column(JSON, default=dict)
