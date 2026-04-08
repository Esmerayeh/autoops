from sqlalchemy.orm import Session

from control_plane.app.models.policy import Policy


class PolicyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, policy: Policy) -> Policy:
        self.db.add(policy)
        self.db.flush()
        return policy

    def list_for_tenant(self, tenant_id: str) -> list[Policy]:
        return list(self.db.query(Policy).filter(Policy.tenant_id == tenant_id).order_by(Policy.created_at.desc()).all())
