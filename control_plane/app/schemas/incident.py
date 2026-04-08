from pydantic import BaseModel


class IncidentSummary(BaseModel):
    incident_id: str
    severity: str
    status: str
    title: str
    summary: str


class IncidentListResponse(BaseModel):
    items: list[IncidentSummary]
    total: int


class IncidentAcknowledgeRequest(BaseModel):
    note: str
    owner: str
