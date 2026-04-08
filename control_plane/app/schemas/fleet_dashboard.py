from pydantic import BaseModel


class FleetNodeItem(BaseModel):
    id: str
    hostname: str
    environment: str
    region: str
    status: str


class FleetAgentItem(BaseModel):
    id: str
    agent_uid: str
    node_id: str
    version: str
    status: str


class FleetOverviewResponse(BaseModel):
    node_count: int
    agent_count: int
    unhealthy_agent_count: int
    nodes: list[FleetNodeItem]
    agents: list[FleetAgentItem]
