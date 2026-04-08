from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from control_plane.app.api.deps import db_session, require_permission, tenant_scope
from control_plane.app.schemas.topology import TopologyEdge, TopologyGraphResponse, TopologyServiceNode
from control_plane.app.services.topology_service import TopologyService

router = APIRouter(prefix="/topology", tags=["topology"])


@router.get("/graph", response_model=TopologyGraphResponse)
def get_topology(
    db: Session = Depends(db_session),
    tenant_id: str = Depends(tenant_scope),
    _: dict = Depends(require_permission("topology:read")),
) -> TopologyGraphResponse:
    service = TopologyService(db)
    graph = service.get_graph(tenant_id)
    return TopologyGraphResponse(
        services=[
            TopologyServiceNode(
                id=item.id,
                name=item.name,
                node_id=item.node_id,
                category=item.category,
                status=item.status,
            )
            for item in graph["services"]
        ],
        edges=[
            TopologyEdge(
                source_service_id=edge.source_service_id,
                target_service_id=edge.target_service_id,
                edge_type=edge.edge_type,
                confidence=edge.confidence,
            )
            for edge in graph["edges"]
        ],
    )
