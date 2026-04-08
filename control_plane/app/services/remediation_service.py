import uuid

from sqlalchemy.orm import Session

from control_plane.app.messaging.publishers import EventPublisher
from control_plane.app.models.remediation import RemediationAction
from control_plane.app.repositories.remediation_repo import RemediationRepository


class RemediationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.publisher = EventPublisher()
        self.remediation_repo = RemediationRepository(db)

    def create_action(self, tenant_id: str, payload: dict) -> RemediationAction:
        action = RemediationAction(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            incident_id=payload.get("incident_id"),
            target_node_id=payload.get("target_node_id"),
            action_type=payload["action_type"],
            status="requested",
            approval_status="pending",
            request_payload=payload.get("payload", {}),
            reason=payload["reason"],
        )
        self.remediation_repo.create(action)
        self.db.commit()
        return action

    def approve_action(self, tenant_id: str, action_id: str) -> RemediationAction | None:
        action = self.remediation_repo.get(tenant_id, action_id)
        if not action:
            return None
        action.approval_status = "approved"
        action.status = "queued"
        self.db.commit()
        self.publisher.publish_remediation(
            tenant_id=tenant_id,
            action_id=action.id,
            payload=action.request_payload,
            action_type=action.action_type,
            target_node_id=action.target_node_id,
        )
        return action

    def list_agent_tasks(self, tenant_id: str, agent_uid: str) -> list[RemediationAction]:
        agent, items = self.remediation_repo.list_for_agent(tenant_id, agent_uid)
        if not agent:
            raise ValueError("Unknown agent")
        return items

    def mark_dispatched(self, tenant_id: str, action_id: str) -> RemediationAction | None:
        action = self.remediation_repo.get(tenant_id, action_id)
        if not action:
            return None
        action.status = "dispatched"
        self.db.commit()
        return action

    def record_result(self, tenant_id: str, action_id: str, payload: dict) -> RemediationAction | None:
        action = self.remediation_repo.get(tenant_id, action_id)
        if not action:
            return None
        action.status = "completed" if payload.get("success") else "failed"
        action.result_payload = payload.get("details", {})
        if payload.get("message"):
            action.result_payload["message"] = payload["message"]
        self.db.commit()
        return action

    def record_agent_result(self, tenant_id: str, agent_uid: str, action_id: str, payload: dict) -> RemediationAction | None:
        agent, _ = self.remediation_repo.list_for_agent(tenant_id, agent_uid)
        if not agent:
            raise ValueError("Unknown agent")
        action = self.remediation_repo.get(tenant_id, action_id)
        if action and action.target_node_id != agent.node_id:
            action = None
        if not action:
            return None
        return self.record_result(tenant_id, action_id, payload)

    def list_recent(self, tenant_id: str, limit: int = 20) -> list[RemediationAction]:
        return self.remediation_repo.list_recent(tenant_id, limit=limit)
