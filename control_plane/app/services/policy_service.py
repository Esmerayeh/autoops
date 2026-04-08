import uuid

from sqlalchemy.orm import Session

from control_plane.app.models.policy import Policy
from control_plane.app.repositories.policy_repo import PolicyRepository


class PolicyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.policy_repo = PolicyRepository(db)

    def create_policy(self, tenant_id: str, payload: dict) -> Policy:
        policy = Policy(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=payload["name"],
            policy_type=payload["policy_type"],
            scope_json=payload.get("scope", {}),
            rules_json=payload.get("rules", {}),
            version=1,
            is_enabled=True,
        )
        self.policy_repo.create(policy)
        self.db.commit()
        return policy

    def list_policies(self, tenant_id: str) -> list[Policy]:
        return self.policy_repo.list_for_tenant(tenant_id)
