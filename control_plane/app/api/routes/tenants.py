from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from control_plane.app.core.config import settings
from control_plane.app.api.deps import db_session
from control_plane.app.schemas.tenant import TenantBootstrapRequest, TenantBootstrapResponse
from control_plane.app.services.audit_service import AuditService
from control_plane.app.services.tenant_service import TenantService

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("/bootstrap", response_model=TenantBootstrapResponse)
def bootstrap_tenant(
    payload: TenantBootstrapRequest,
    x_bootstrap_token: str | None = Header(default=None),
    db: Session = Depends(db_session),
) -> TenantBootstrapResponse:
    if x_bootstrap_token != settings.bootstrap_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bootstrap token")
    service = TenantService(db)
    tenant, admin_user_id = service.bootstrap_tenant(
        payload.tenant_name,
        payload.tenant_slug,
        payload.admin_email,
        payload.admin_password,
    )
    AuditService(db).record(
        tenant_id=tenant.id,
        actor_type="bootstrap",
        actor_id=None,
        action="tenant.bootstrap",
        resource_type="tenant",
        resource_id=tenant.id,
        outcome="success",
        details={"tenant_slug": tenant.slug, "admin_user_id": admin_user_id},
    )
    return TenantBootstrapResponse(tenant_id=tenant.id, admin_user_id=admin_user_id)
