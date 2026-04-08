from sqlalchemy.orm import Session

from control_plane.app.core.config import settings
from control_plane.app.models.tenant import Tenant
from control_plane.app.models.user import User
from control_plane.app.services.tenant_service import TenantService


class BootstrapService:
    """Seeds a local demo tenant for the distributed control plane."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.tenant_service = TenantService(db)

    def ensure_demo_tenant(self) -> dict:
        existing_tenant = self.db.query(Tenant).filter(Tenant.slug == "demo").first()
        existing_user = self.db.query(User).filter(User.email == settings.bootstrap_admin_email).first()
        if existing_tenant and existing_user:
            return {"tenant_id": existing_tenant.id, "admin_user_id": existing_user.id, "created": False}

        tenant, admin_user_id = self.tenant_service.bootstrap_tenant(
            name="Demo Tenant",
            slug="demo",
            admin_email=settings.bootstrap_admin_email,
            admin_password=settings.bootstrap_admin_password,
        )
        return {"tenant_id": tenant.id, "admin_user_id": admin_user_id, "created": True}
