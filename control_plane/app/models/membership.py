import uuid

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from control_plane.app.core.db import Base


class Membership(Base):
    __tablename__ = "cp_memberships"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", name="uq_cp_membership"),)

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(index=True)
    user_id: Mapped[str] = mapped_column(index=True)
    role_id: Mapped[str] = mapped_column(index=True)
