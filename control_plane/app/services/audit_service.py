import uuid

from sqlalchemy.orm import Session

from control_plane.app.messaging.publishers import EventPublisher
from control_plane.app.models.audit import AuditRecord
from control_plane.app.repositories.audit_repo import AuditRepository


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.publisher = EventPublisher()
        self.audit_repo = AuditRepository(db)

    def record(
        self,
        tenant_id: str,
        actor_type: str,
        actor_id: str | None,
        action: str,
        resource_type: str,
        resource_id: str | None,
        outcome: str,
        details: dict | None = None,
    ) -> AuditRecord:
        record = AuditRecord(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            details_json=details or {},
        )
        self.audit_repo.create(record)
        self.db.commit()
        self.publisher.publish_audit(
            tenant_id=tenant_id,
            action=action,
            actor_id=actor_id,
            outcome=outcome,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        return record

    def list_records(self, tenant_id: str) -> list[AuditRecord]:
        return self.audit_repo.list_recent(tenant_id)
