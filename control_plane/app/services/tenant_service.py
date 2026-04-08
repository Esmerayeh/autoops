import uuid

from sqlalchemy.orm import Session

from control_plane.app.models.tenant import Tenant
from control_plane.app.repositories.tenant_repo import TenantRepository
from control_plane.app.services.auth_service import AuthService


class TenantService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.auth_service = AuthService(db)
        self.tenant_repo = TenantRepository(db)

    def bootstrap_tenant(self, name: str, slug: str, admin_email: str, admin_password: str) -> tuple[Tenant, str]:
        tenant = Tenant(id=str(uuid.uuid4()), name=name, slug=slug, status="active")
        self.tenant_repo.create(tenant)
        self.db.commit()
        user = self.auth_service.create_user(
            email=admin_email,
            password=admin_password,
            tenant_id=tenant.id,
            permissions=[
                "fleet:read",
                "fleet:write",
                "policy:read",
                "policy:write",
                "incidents:read",
                "incidents:ack",
                "topology:read",
                "remediation:request",
                "remediation:approve",
                "audit:read",
            ],
        )
        return tenant, user.id
