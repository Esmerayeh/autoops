from sqlalchemy import JSON, Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from control_plane.app.models.base import UUIDTenantBase


class Service(UUIDTenantBase):
    __tablename__ = "cp_services"

    node_id: Mapped[str] = mapped_column(index=True)
    service_key: Mapped[str] = mapped_column(String(160), index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True, default="process")
    status: Mapped[str] = mapped_column(String(32), default="unknown")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class DependencyEdge(UUIDTenantBase):
    __tablename__ = "cp_dependency_edges"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source_service_id", "target_service_id", name="uq_cp_dependency_edge"),
    )

    source_service_id: Mapped[str] = mapped_column(index=True)
    target_service_id: Mapped[str] = mapped_column(index=True)
    edge_type: Mapped[str] = mapped_column(String(64), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    evidence_json: Mapped[dict] = mapped_column(JSON, default=dict)
