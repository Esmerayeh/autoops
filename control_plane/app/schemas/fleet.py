from pydantic import BaseModel, Field


class AgentRegistrationRequest(BaseModel):
    tenant_slug: str
    node_uid: str
    hostname: str
    environment: str
    region: str
    agent_version: str
    capabilities: dict = Field(default_factory=dict)


class AgentRegistrationResponse(BaseModel):
    agent_id: str
    node_id: str
    agent_token: str
    policy_version: int


class HeartbeatRequest(BaseModel):
    status: str
    metrics: dict = Field(default_factory=dict)
    service_states: list[dict] = Field(default_factory=list)


class HeartbeatResponse(BaseModel):
    accepted: bool
    next_policy_version: int
