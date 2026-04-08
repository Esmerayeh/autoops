from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from control_plane.app.api.deps import db_session, get_current_principal, require_permission, require_token_type, tenant_scope
from control_plane.app.schemas.remediation import (
    RemediationApprovalResponse,
    RemediationCreateRequest,
    RemediationResponse,
    RemediationResultRequest,
    RemediationTaskItem,
    RemediationTaskListResponse,
)
from control_plane.app.services.audit_service import AuditService
from control_plane.app.services.remediation_service import RemediationService

router = APIRouter(prefix="/remediation", tags=["remediation"])


@router.post("/actions", response_model=RemediationResponse)
def create_action(
    payload: RemediationCreateRequest,
    db: Session = Depends(db_session),
    tenant_id: str = Depends(tenant_scope),
    principal=Depends(get_current_principal),
    _: dict = Depends(require_permission("remediation:request")),
) -> RemediationResponse:
    service = RemediationService(db)
    action = service.create_action(tenant_id, payload.model_dump())
    AuditService(db).record(
        tenant_id=tenant_id,
        actor_type="user",
        actor_id=principal.subject,
        action="remediation.request",
        resource_type="remediation_action",
        resource_id=action.id,
        outcome="success",
        details={"action_type": action.action_type, "target_node_id": action.target_node_id},
    )
    return RemediationResponse(
        action_id=action.id,
        status=action.status,
        approval_status=action.approval_status,
    )


@router.post("/actions/{action_id}/approve", response_model=RemediationApprovalResponse)
def approve_action(
    action_id: str,
    db: Session = Depends(db_session),
    tenant_id: str = Depends(tenant_scope),
    principal=Depends(get_current_principal),
    _: object = Depends(require_permission("remediation:approve")),
) -> RemediationApprovalResponse:
    service = RemediationService(db)
    action = service.approve_action(tenant_id, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    AuditService(db).record(
        tenant_id=tenant_id,
        actor_type="user",
        actor_id=principal.subject,
        action="remediation.approve",
        resource_type="remediation_action",
        resource_id=action.id,
        outcome="success",
        details={"status": action.status},
    )
    return RemediationApprovalResponse(
        action_id=action.id,
        status=action.status,
        approval_status=action.approval_status,
    )


@router.get("/agents/{agent_id}/tasks", response_model=RemediationTaskListResponse)
def list_agent_tasks(
    agent_id: str,
    db: Session = Depends(db_session),
    principal=Depends(require_token_type("agent")),
) -> RemediationTaskListResponse:
    if principal.subject != agent_id:
        raise HTTPException(status_code=403, detail="Agent token does not match target agent")
    service = RemediationService(db)
    try:
        items = service.list_agent_tasks(principal.tenant_id, agent_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    for item in items:
        service.mark_dispatched(principal.tenant_id, item.id)
    return RemediationTaskListResponse(
        items=[
            RemediationTaskItem(
                action_id=item.id,
                action_type=item.action_type,
                target_node_id=item.target_node_id,
                request_payload=item.request_payload,
                reason=item.reason,
            )
            for item in items
        ]
    )


@router.post("/actions/{action_id}/result", response_model=RemediationApprovalResponse)
def record_action_result(
    action_id: str,
    payload: RemediationResultRequest,
    db: Session = Depends(db_session),
    principal=Depends(require_token_type("agent")),
) -> RemediationApprovalResponse:
    service = RemediationService(db)
    try:
        action = service.record_agent_result(principal.tenant_id, principal.subject, action_id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    AuditService(db).record(
        tenant_id=principal.tenant_id,
        actor_type="agent",
        actor_id=principal.subject,
        action="remediation.result",
        resource_type="remediation_action",
        resource_id=action.id,
        outcome="success" if action.status == "completed" else "failure",
        details={"status": action.status, "approval_status": action.approval_status},
    )
    return RemediationApprovalResponse(
        action_id=action.id,
        status=action.status,
        approval_status=action.approval_status,
    )


@router.get("/recent")
def list_recent_actions(
    db: Session = Depends(db_session),
    tenant_id: str = Depends(tenant_scope),
    _: object = Depends(require_permission("remediation:request")),
) -> dict:
    items = RemediationService(db).list_recent(tenant_id, limit=20)
    return {
        "items": [
            {
                "id": item.id,
                "action_type": item.action_type,
                "status": item.status,
                "approval_status": item.approval_status,
                "target_node_id": item.target_node_id,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ]
    }
