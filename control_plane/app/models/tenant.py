import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from control_plane.app.core.db import Base


class Tenant(Base):
    __tablename__ = "cp_tenants"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
