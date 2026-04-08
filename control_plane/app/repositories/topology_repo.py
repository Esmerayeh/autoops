from sqlalchemy.orm import Session

from control_plane.app.models.topology import DependencyEdge, Service


class TopologyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_services(self, tenant_id: str) -> list[Service]:
        return list(self.db.query(Service).filter(Service.tenant_id == tenant_id).all())

    def list_edges(self, tenant_id: str) -> list[DependencyEdge]:
        return list(self.db.query(DependencyEdge).filter(DependencyEdge.tenant_id == tenant_id).all())

    def get_service(self, tenant_id: str, node_id: str, service_key: str) -> Service | None:
        return (
            self.db.query(Service)
            .filter(Service.tenant_id == tenant_id, Service.node_id == node_id, Service.service_key == service_key)
            .first()
        )

    def create_service(self, service: Service) -> Service:
        self.db.add(service)
        self.db.flush()
        return service

    def get_edge(self, tenant_id: str, source_service_id: str, target_service_id: str) -> DependencyEdge | None:
        return (
            self.db.query(DependencyEdge)
            .filter(
                DependencyEdge.tenant_id == tenant_id,
                DependencyEdge.source_service_id == source_service_id,
                DependencyEdge.target_service_id == target_service_id,
            )
            .first()
        )

    def create_edge(self, edge: DependencyEdge) -> DependencyEdge:
        self.db.add(edge)
        self.db.flush()
        return edge
