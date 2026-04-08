from pydantic import BaseModel


class AuditItem(BaseModel):
    id: str
    action: str
    actor_id: str | None = None
    outcome: str


class AuditListResponse(BaseModel):
    items: list[AuditItem]
