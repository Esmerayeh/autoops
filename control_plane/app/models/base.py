import uuid

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from control_plane.app.core.db import Base


class UUIDTenantBase(Base):
    """Base model for tenant-scoped records."""

    __abstract__ = True

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(index=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
