from fastapi import APIRouter

from control_plane.app.api.routes import audit, auth, fleet, incidents, policies, remediation, telemetry, tenants, topology

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(tenants.router)
api_router.include_router(fleet.router)
api_router.include_router(telemetry.router)
api_router.include_router(incidents.router)
api_router.include_router(policies.router)
api_router.include_router(topology.router)
api_router.include_router(remediation.router)
api_router.include_router(audit.router)
