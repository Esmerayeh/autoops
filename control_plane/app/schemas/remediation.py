from pydantic import BaseModel, Field


class RemediationCreateRequest(BaseModel):
    incident_id: str | None = None
    target_node_id: str | None = None
    action_type: str
    payload: dict = Field(default_factory=dict)
    reason: str


class RemediationResponse(BaseModel):
    action_id: str
    status: str
    approval_status: str


class RemediationTaskItem(BaseModel):
    action_id: str
    action_type: str
    target_node_id: str | None = None
    request_payload: dict = Field(default_factory=dict)
    reason: str | None = None


class RemediationTaskListResponse(BaseModel):
    items: list[RemediationTaskItem]


class RemediationResultRequest(BaseModel):
    success: bool
    details: dict = Field(default_factory=dict)
    message: str | None = None


class RemediationApprovalResponse(BaseModel):
    action_id: str
    status: str
    approval_status: str
