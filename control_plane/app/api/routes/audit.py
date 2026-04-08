from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from control_plane.app.api.deps import db_session, require_permission, tenant_scope
from control_plane.app.schemas.audit import AuditItem, AuditListResponse
from control_plane.app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditListResponse)
def list_audit_records(
    db: Session = Depends(db_session),
    tenant_id: str = Depends(tenant_scope),
    _: dict = Depends(require_permission("audit:read")),
) -> AuditListResponse:
    service = AuditService(db)
    items = [
        AuditItem(id=item.id, action=item.action, actor_id=item.actor_id, outcome=item.outcome)
        for item in service.list_records(tenant_id)
    ]
    return AuditListResponse(items=items)
