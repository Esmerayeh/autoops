import uuid

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from control_plane.app.core.db import Base


class EnrollmentToken(Base):
    __tablename__ = "cp_enrollment_tokens"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(index=True)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True)
    created_by_user_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    expires_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
