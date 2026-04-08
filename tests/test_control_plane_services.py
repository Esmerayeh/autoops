import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from control_plane.app.core.db import Base
from control_plane.app.models.incident import Incident
from control_plane.app.models.topology import DependencyEdge, Service
from control_plane.app.services.auth_service import AuthService
from control_plane.app.services.fleet_service import FleetService
from control_plane.app.services.incident_service import IncidentService
from control_plane.app.services.remediation_service import RemediationService
from control_plane.app.services.telemetry_service import TelemetryService
from control_plane.app.services.tenant_service import TenantService


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    return TestingSession()


def test_tenant_bootstrap_and_login():
    db = make_session()
    tenant, admin_user_id = TenantService(db).bootstrap_tenant(
        "Demo Tenant",
        "demo",
        "admin@example.com",
        "StrongPass123!",
    )

    assert tenant.slug == "demo"
    assert admin_user_id

    token_payload = AuthService(db).authenticate("admin@example.com", "StrongPass123!")
    assert token_payload is not None
    assert "access_token" in token_payload


def test_agent_registration_and_heartbeat():
    db = make_session()
    tenant, _ = TenantService(db).bootstrap_tenant("Demo Tenant", "demo", "admin@example.com", "StrongPass123!")
    fleet = FleetService(db)
    registration = fleet.register_agent(
        "demo",
        {
            "node_uid": "node-1",
            "hostname": "host-1",
            "environment": "dev",
            "region": "local",
            "agent_version": "0.1.0",
            "capabilities": {"host_metrics": True},
        },
    )

    assert registration["agent_id"]
    heartbeat = fleet.record_heartbeat(
        tenant.id,
        registration["agent_id"],
        {"status": "healthy", "metrics": {"cpu": 20}},
    )
    assert heartbeat["accepted"] is True


def test_incident_and_topology_services():
    db = make_session()
    tenant, _ = TenantService(db).bootstrap_tenant("Demo Tenant", "demo", "admin@example.com", "StrongPass123!")

    incident = Incident(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        incident_key="cpu:critical",
        severity="critical",
        status="open",
        title="CPU issue",
        summary="CPU too high",
        root_cause_json={},
        affected_nodes_json=[],
    )
    service = Service(
        tenant_id=tenant.id,
        node_id="node-1",
        service_key="svc-api",
        name="api",
        category="process",
        status="healthy",
        metadata_json={},
    )
    edge = DependencyEdge(
        tenant_id=tenant.id,
        source_service_id="svc-a",
        target_service_id="svc-b",
        edge_type="network",
        confidence=0.8,
        evidence_json={},
    )
    db.add_all([incident, service, edge])
    db.commit()

    incidents = IncidentService(db).list_incidents(tenant.id)
    assert len(incidents) == 1
    assert incidents[0].title == "CPU issue"


def test_remediation_request_approve_and_result():
    db = make_session()
    tenant, _ = TenantService(db).bootstrap_tenant("Demo Tenant", "demo", "admin@example.com", "StrongPass123!")
    registration = FleetService(db).register_agent(
        "demo",
        {
            "node_uid": "node-1",
            "hostname": "host-1",
            "environment": "dev",
            "region": "local",
            "agent_version": "0.1.0",
            "capabilities": {"host_metrics": True},
        },
    )

    remediation = RemediationService(db)
    remediation.publisher = type(
        "StubPublisher",
        (),
        {
            "publish_remediation": staticmethod(lambda **_: "msg-1"),
        },
    )()
    action = remediation.create_action(
        tenant.id,
        {
            "target_node_id": registration["node_id"],
            "action_type": "collect_diagnostics",
            "payload": {"scope": "cpu"},
            "reason": "Investigate CPU pressure",
        },
    )
    assert action.approval_status == "pending"

    approved = remediation.approve_action(tenant.id, action.id)
    assert approved is not None
    assert approved.approval_status == "approved"

    tasks = remediation.list_agent_tasks(tenant.id, registration["agent_id"])
    assert len(tasks) == 1
    assert tasks[0].action_type == "collect_diagnostics"

    result = remediation.record_agent_result(
        tenant.id,
        registration["agent_id"],
        action.id,
        {
            "success": True,
            "details": {"bundle": "diag-1"},
            "message": "Collected diagnostics",
        },
    )
    assert result is not None
    assert result.status == "completed"


def test_telemetry_ingest_batch():
    db = make_session()
    tenant, _ = TenantService(db).bootstrap_tenant("Demo Tenant", "demo", "admin@example.com", "StrongPass123!")
    registration = FleetService(db).register_agent(
        "demo",
        {
            "node_uid": "node-1",
            "hostname": "host-1",
            "environment": "dev",
            "region": "local",
            "agent_version": "0.1.0",
            "capabilities": {"host_metrics": True},
        },
    )

    telemetry = TelemetryService(db)
    telemetry.publisher = type(
        "StubPublisher",
        (),
        {
            "publish_telemetry": staticmethod(lambda **_: "msg-telemetry"),
        },
    )()

    result = telemetry.ingest_batch(
        tenant.id,
        registration["agent_id"],
        {
            "batch_id": "batch-1",
            "events": [
                {
                    "event_type": "host_metrics",
                    "event_id": "event-1",
                    "occurred_at": "2026-04-08T10:00:00Z",
                    "payload": {"cpu_percent": 95.2},
                }
            ],
        },
    )

    assert result["accepted"] is True
    assert "ingest_id" in result
