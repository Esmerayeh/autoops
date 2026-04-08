from sqlalchemy.orm import Session

from control_plane.app.models.incident import Incident
from control_plane.app.repositories.incident_repo import IncidentRepository


class IncidentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.incident_repo = IncidentRepository(db)

    def list_incidents(self, tenant_id: str) -> list[Incident]:
        return self.incident_repo.list_incidents(tenant_id)

    def acknowledge(self, tenant_id: str, incident_id: str) -> Incident | None:
        incident = self.incident_repo.get_incident(tenant_id, incident_id)
        if incident:
            incident.status = "acknowledged"
            self.db.commit()
        return incident
