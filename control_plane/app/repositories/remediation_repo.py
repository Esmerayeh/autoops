from sqlalchemy.orm import Session

from control_plane.app.models.agent import Agent
from control_plane.app.models.remediation import RemediationAction


class RemediationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, action: RemediationAction) -> RemediationAction:
        self.db.add(action)
        self.db.flush()
        return action

    def get(self, tenant_id: str, action_id: str) -> RemediationAction | None:
        return self.db.query(RemediationAction).filter(RemediationAction.id == action_id, RemediationAction.tenant_id == tenant_id).first()

    def list_for_agent(self, tenant_id: str, agent_uid: str) -> tuple[Agent | None, list[RemediationAction]]:
        agent = self.db.query(Agent).filter(Agent.agent_uid == agent_uid, Agent.tenant_id == tenant_id).first()
        if not agent:
            return None, []
        items = list(
            self.db.query(RemediationAction)
            .filter(
                RemediationAction.tenant_id == tenant_id,
                RemediationAction.target_node_id == agent.node_id,
                RemediationAction.approval_status == "approved",
                RemediationAction.status.in_(["queued", "dispatched"]),
            )
            .all()
        )
        return agent, items

    def list_recent(self, tenant_id: str, limit: int = 20) -> list[RemediationAction]:
        return list(
            self.db.query(RemediationAction)
            .filter(RemediationAction.tenant_id == tenant_id)
            .order_by(RemediationAction.created_at.desc())
            .limit(limit)
            .all()
        )
