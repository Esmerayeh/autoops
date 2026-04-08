from pydantic import BaseModel


class TopologyServiceNode(BaseModel):
    id: str
    name: str
    node_id: str
    category: str
    status: str


class TopologyEdge(BaseModel):
    source_service_id: str
    target_service_id: str
    edge_type: str
    confidence: float


class TopologyGraphResponse(BaseModel):
    services: list[TopologyServiceNode]
    edges: list[TopologyEdge]
