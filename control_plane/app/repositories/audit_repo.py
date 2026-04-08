from sqlalchemy.orm import Session

from control_plane.app.models.audit import AuditRecord


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, record: AuditRecord) -> AuditRecord:
        self.db.add(record)
        self.db.flush()
        return record

    def list_recent(self, tenant_id: str, limit: int = 50) -> list[AuditRecord]:
        return list(
            self.db.query(AuditRecord)
            .filter(AuditRecord.tenant_id == tenant_id)
            .order_by(AuditRecord.created_at.desc())
            .limit(limit)
            .all()
        )
