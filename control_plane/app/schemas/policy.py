from pydantic import BaseModel, Field


class PolicyCreateRequest(BaseModel):
    name: str
    policy_type: str
    scope: dict = Field(default_factory=dict)
    rules: dict = Field(default_factory=dict)


class PolicyResponse(BaseModel):
    id: str
    name: str
    policy_type: str
    version: int
    is_enabled: bool
