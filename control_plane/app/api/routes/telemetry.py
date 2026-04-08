from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from control_plane.app.api.deps import db_session, require_token_type
from control_plane.app.schemas.telemetry import TelemetryBatchRequest, TelemetryBatchResponse
from control_plane.app.services.telemetry_service import TelemetryService

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post("/batches", response_model=TelemetryBatchResponse)
def ingest_batch(
    payload: TelemetryBatchRequest,
    db: Session = Depends(db_session),
    principal=Depends(require_token_type("agent")),
) -> TelemetryBatchResponse:
    service = TelemetryService(db)
    result = service.ingest_batch(principal.tenant_id, principal.subject, payload.model_dump())
    return TelemetryBatchResponse(**result)
