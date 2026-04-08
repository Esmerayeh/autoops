from sqlalchemy.orm import Session

from control_plane.app.models.tenant import Tenant


class TenantRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_slug(self, slug: str) -> Tenant | None:
        return self.db.query(Tenant).filter(Tenant.slug == slug).first()

    def get_by_id(self, tenant_id: str) -> Tenant | None:
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def create(self, tenant: Tenant) -> Tenant:
        self.db.add(tenant)
        self.db.flush()
        return tenant
