from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from control_plane.app.api.deps import db_session, get_current_principal, require_permission, tenant_scope
from control_plane.app.schemas.incident import IncidentAcknowledgeRequest, IncidentListResponse, IncidentSummary
from control_plane.app.services.audit_service import AuditService
from control_plane.app.services.incident_service import IncidentService

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=IncidentListResponse)
def list_incidents(
    db: Session = Depends(db_session),
    tenant_id: str = Depends(tenant_scope),
    _: dict = Depends(require_permission("incidents:read")),
) -> IncidentListResponse:
    service = IncidentService(db)
    items = [
        IncidentSummary(
            incident_id=incident.id,
            severity=incident.severity,
            status=incident.status,
            title=incident.title,
            summary=incident.summary,
        )
        for incident in service.list_incidents(tenant_id)
    ]
    return IncidentListResponse(items=items, total=len(items))


@router.post("/{incident_id}/ack", response_model=IncidentSummary)
def acknowledge_incident(
    incident_id: str,
    payload: IncidentAcknowledgeRequest,
    db: Session = Depends(db_session),
    tenant_id: str = Depends(tenant_scope),
    principal=Depends(get_current_principal),
    _: dict = Depends(require_permission("incidents:ack")),
) -> IncidentSummary:
    service = IncidentService(db)
    incident = service.acknowledge(tenant_id, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    AuditService(db).record(
        tenant_id=tenant_id,
        actor_type="user",
        actor_id=principal.subject,
        action="incident.ack",
        resource_type="incident",
        resource_id=incident.id,
        outcome="success",
        details={"note": payload.note},
    )
    return IncidentSummary(
        incident_id=incident.id,
        severity=incident.severity,
        status=incident.status,
        title=incident.title,
        summary=incident.summary,
    )
