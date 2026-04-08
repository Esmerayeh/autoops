from sqlalchemy.orm import Session

from control_plane.app.models.alert import Alert
from control_plane.app.models.incident import Incident


class IncidentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_incidents(self, tenant_id: str) -> list[Incident]:
        return list(self.db.query(Incident).filter(Incident.tenant_id == tenant_id).order_by(Incident.created_at.desc()).all())

    def get_incident(self, tenant_id: str, incident_id: str) -> Incident | None:
        return self.db.query(Incident).filter(Incident.id == incident_id, Incident.tenant_id == tenant_id).first()

    def get_open_incident_by_key(self, tenant_id: str, incident_key: str) -> Incident | None:
        return (
            self.db.query(Incident)
            .filter(Incident.tenant_id == tenant_id, Incident.incident_key == incident_key, Incident.status.in_(["open", "acknowledged"]))
            .first()
        )

    def create_incident(self, incident: Incident) -> Incident:
        self.db.add(incident)
        self.db.flush()
        return incident

    def get_open_alert_by_key(self, tenant_id: str, dedupe_key: str) -> Alert | None:
        return self.db.query(Alert).filter(Alert.tenant_id == tenant_id, Alert.dedupe_key == dedupe_key, Alert.status == "open").first()

    def create_alert(self, alert: Alert) -> Alert:
        self.db.add(alert)
        self.db.flush()
        return alert
