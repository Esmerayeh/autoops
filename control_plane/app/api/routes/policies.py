from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from control_plane.app.api.deps import db_session, get_current_principal, require_permission, tenant_scope
from control_plane.app.schemas.policy import PolicyCreateRequest, PolicyResponse
from control_plane.app.services.audit_service import AuditService
from control_plane.app.services.policy_service import PolicyService

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("", response_model=list[PolicyResponse])
def list_policies(
    db: Session = Depends(db_session),
    tenant_id: str = Depends(tenant_scope),
    _: dict = Depends(require_permission("policy:read")),
) -> list[PolicyResponse]:
    service = PolicyService(db)
    return [
        PolicyResponse(
            id=policy.id,
            name=policy.name,
            policy_type=policy.policy_type,
            version=policy.version,
            is_enabled=policy.is_enabled,
        )
        for policy in service.list_policies(tenant_id)
    ]


@router.post("", response_model=PolicyResponse)
def create_policy(
    payload: PolicyCreateRequest,
    db: Session = Depends(db_session),
    tenant_id: str = Depends(tenant_scope),
    principal=Depends(get_current_principal),
    _: dict = Depends(require_permission("policy:write")),
) -> PolicyResponse:
    service = PolicyService(db)
    policy = service.create_policy(tenant_id, payload.model_dump())
    AuditService(db).record(
        tenant_id=tenant_id,
        actor_type="user",
        actor_id=principal.subject,
        action="policy.create",
        resource_type="policy",
        resource_id=policy.id,
        outcome="success",
        details={"policy_type": policy.policy_type, "version": policy.version},
    )
    return PolicyResponse(
        id=policy.id,
        name=policy.name,
        policy_type=policy.policy_type,
        version=policy.version,
        is_enabled=policy.is_enabled,
    )
