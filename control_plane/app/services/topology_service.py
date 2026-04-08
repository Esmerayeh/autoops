from sqlalchemy.orm import Session

from control_plane.app.repositories.topology_repo import TopologyRepository


class TopologyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.topology_repo = TopologyRepository(db)

    def get_graph(self, tenant_id: str) -> dict:
        services = self.topology_repo.list_services(tenant_id)
        edges = self.topology_repo.list_edges(tenant_id)
        return {"services": services, "edges": edges}
