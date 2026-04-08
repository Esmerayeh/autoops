from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from control_plane.app.api.deps import db_session, require_permission, require_token_type, tenant_scope
from control_plane.app.schemas.fleet_dashboard import FleetAgentItem, FleetNodeItem, FleetOverviewResponse
from control_plane.app.core.config import settings
from control_plane.app.schemas.fleet import (
    AgentRegistrationRequest,
    AgentRegistrationResponse,
    HeartbeatRequest,
    HeartbeatResponse,
)
from control_plane.app.services.audit_service import AuditService
from control_plane.app.services.fleet_service import FleetService
from control_plane.app.services.policy_service import PolicyService

router = APIRouter(prefix="/fleet", tags=["fleet"])


@router.post("/agents/register", response_model=AgentRegistrationResponse)
def register_agent(
    payload: AgentRegistrationRequest,
    db: Session = Depends(db_session),
    x_enrollment_token: str | None = Header(default=None),
) -> AgentRegistrationResponse:
    if x_enrollment_token != settings.agent_enrollment_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid enrollment token")
    service = FleetService(db)
    try:
        result = service.register_agent(tenant_slug=payload.tenant_slug, payload=payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    tenant = service.tenant_repo.get_by_slug(payload.tenant_slug)
    AuditService(db).record(
        tenant_id=tenant.id,
        actor_type="agent_enrollment",
        actor_id=result["agent_id"],
        action="fleet.agent.register",
        resource_type="agent",
        resource_id=result["agent_id"],
        outcome="success",
        details={"node_id": result["node_id"], "tenant_slug": payload.tenant_slug},
    )
    return AgentRegistrationResponse(**result)


@router.post("/agents/{agent_id}/heartbeat", response_model=HeartbeatResponse)
def heartbeat(
    agent_id: str,
    payload: HeartbeatRequest,
    db: Session = Depends(db_session),
    principal=Depends(require_token_type("agent")),
) -> HeartbeatResponse:
    if principal.subject != agent_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent token does not match target agent")
    service = FleetService(db)
    result = service.record_heartbeat(principal.tenant_id, agent_id, payload.model_dump())
    return HeartbeatResponse(**result)


@router.get("/agents/{agent_id}/policies")
def get_agent_policies(
    agent_id: str,
    db: Session = Depends(db_session),
    principal=Depends(require_token_type("agent")),
) -> dict:
    if principal.subject != agent_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent token does not match target agent")
    service = PolicyService(db)
    policies = service.list_policies(principal.tenant_id)
    return {
        "changed": True,
        "version": max([policy.version for policy in policies], default=1),
        "policies": [
            {
                "policy_id": policy.id,
                "type": policy.policy_type,
                "scope": policy.scope_json,
                "rules": policy.rules_json,
            }
            for policy in policies
        ],
    }


@router.get("/overview", response_model=FleetOverviewResponse)
def get_fleet_overview(
    db: Session = Depends(db_session),
    tenant_id: str = Depends(tenant_scope),
    _: object = Depends(require_permission("fleet:read")),
) -> FleetOverviewResponse:
    overview = FleetService(db).get_fleet_overview(tenant_id)
    return FleetOverviewResponse(
        node_count=overview["node_count"],
        agent_count=overview["agent_count"],
        unhealthy_agent_count=overview["unhealthy_agent_count"],
        nodes=[
            FleetNodeItem(
                id=node.id,
                hostname=node.hostname,
                environment=node.environment,
                region=node.region,
                status=node.status,
            )
            for node in overview["nodes"]
        ],
        agents=[
            FleetAgentItem(
                id=agent.id,
                agent_uid=agent.agent_uid,
                node_id=agent.node_id,
                version=agent.version,
                status=agent.status,
            )
            for agent in overview["agents"]
        ],
    )
