import os

os.environ["AUTOOPS_SKIP_STARTUP_INIT"] = "1"

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from control_plane.app.core.db import Base, get_db
from control_plane.app.main import create_app
from control_plane.app.messaging.publishers import EventPublisher


def make_test_app():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    app = create_app(initialize_db=False, enable_bootstrap=False)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return app


def stub_publishers(monkeypatch):
    monkeypatch.setattr(EventPublisher, "publish_telemetry", lambda self, **kwargs: "telemetry-msg")
    monkeypatch.setattr(EventPublisher, "publish_remediation", lambda self, **kwargs: "remediation-msg")
    monkeypatch.setattr(EventPublisher, "publish_audit", lambda self, **kwargs: "audit-msg")


def bootstrap_and_login(client: TestClient):
    bootstrap = client.post(
        "/api/v1/tenants/bootstrap",
        headers={"X-Bootstrap-Token": "change-me-bootstrap"},
        json={
            "tenant_name": "Demo Tenant",
            "tenant_slug": "demo",
            "admin_email": "admin@example.com",
            "admin_password": "StrongPass123!",
        },
    )
    assert bootstrap.status_code == 200

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "StrongPass123!"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_bootstrap_login_and_policy_flow(monkeypatch):
    stub_publishers(monkeypatch)
    app = make_test_app()
    client = TestClient(app)
    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert "Fleet Command Center" in dashboard.text
    headers = bootstrap_and_login(client)

    policy = client.post(
        "/api/v1/policies",
        headers=headers,
        json={
            "name": "CPU Guardrail",
            "policy_type": "remediation",
            "scope": {"node_groups": ["web"]},
            "rules": {"cpu_critical": 90},
        },
    )
    assert policy.status_code == 200
    assert policy.json()["name"] == "CPU Guardrail"

    policies = client.get("/api/v1/policies", headers=headers)
    assert policies.status_code == 200
    assert len(policies.json()) == 1


def test_agent_registration_heartbeat_and_telemetry(monkeypatch):
    stub_publishers(monkeypatch)
    app = make_test_app()
    client = TestClient(app)
    headers = bootstrap_and_login(client)

    agent_registration = client.post(
        "/api/v1/fleet/agents/register",
        headers={"X-Enrollment-Token": "change-me-agent"},
        json={
            "tenant_slug": "demo",
            "node_uid": "node-1",
            "hostname": "host-1",
            "environment": "dev",
            "region": "local",
            "agent_version": "0.1.0",
            "capabilities": {"host_metrics": True},
        },
    )
    assert agent_registration.status_code == 200
    registration_payload = agent_registration.json()
    agent_headers = {"Authorization": f"Bearer {registration_payload['agent_token']}"}

    heartbeat = client.post(
        f"/api/v1/fleet/agents/{registration_payload['agent_id']}/heartbeat",
        headers=agent_headers,
        json={"status": "healthy", "metrics": {"cpu": 12}, "service_states": []},
    )
    assert heartbeat.status_code == 200
    assert heartbeat.json()["accepted"] is True

    telemetry = client.post(
        "/api/v1/telemetry/batches",
        headers=agent_headers,
        json={
            "batch_id": "batch-1",
            "sent_at": "2026-04-08T12:00:00Z",
            "events": [
                {
                    "event_type": "host_metrics",
                    "event_id": "evt-1",
                    "occurred_at": "2026-04-08T12:00:00Z",
                    "payload": {"cpu_percent": 95.0},
                }
            ],
        },
    )
    assert telemetry.status_code == 200
    assert telemetry.json()["accepted"] is True

    overview = client.get("/api/v1/fleet/overview", headers=headers)
    assert overview.status_code == 200
    assert overview.json()["node_count"] == 1


def test_remediation_approval_and_agent_result(monkeypatch):
    stub_publishers(monkeypatch)
    app = make_test_app()
    client = TestClient(app)
    headers = bootstrap_and_login(client)

    agent_registration = client.post(
        "/api/v1/fleet/agents/register",
        headers={"X-Enrollment-Token": "change-me-agent"},
        json={
            "tenant_slug": "demo",
            "node_uid": "node-1",
            "hostname": "host-1",
            "environment": "dev",
            "region": "local",
            "agent_version": "0.1.0",
            "capabilities": {"host_metrics": True},
        },
    ).json()
    agent_headers = {"Authorization": f"Bearer {agent_registration['agent_token']}"}

    action = client.post(
        "/api/v1/remediation/actions",
        headers=headers,
        json={
            "target_node_id": agent_registration["node_id"],
            "action_type": "collect_diagnostics",
            "payload": {"scope": "cpu"},
            "reason": "Investigate pressure",
        },
    )
    assert action.status_code == 200
    action_id = action.json()["action_id"]

    approve = client.post(f"/api/v1/remediation/actions/{action_id}/approve", headers=headers)
    assert approve.status_code == 200
    assert approve.json()["approval_status"] == "approved"

    tasks = client.get(f"/api/v1/remediation/agents/{agent_registration['agent_id']}/tasks", headers=agent_headers)
    assert tasks.status_code == 200
    assert len(tasks.json()["items"]) == 1

    result = client.post(
        f"/api/v1/remediation/actions/{action_id}/result",
        headers=agent_headers,
        json={"success": True, "details": {"bundle": "diag-1"}, "message": "Done"},
    )
    assert result.status_code == 200
    assert result.json()["status"] == "completed"

    audit = client.get("/api/v1/audit", headers=headers)
    assert audit.status_code == 200
    assert len(audit.json()["items"]) >= 1
