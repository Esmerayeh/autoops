def test_health_requires_auth(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 401


def test_stats_api(auth_client):
    response = auth_client.get("/api/v1/stats")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert "snapshot" in payload["data"]
    assert "analysis" in payload["data"]


def test_legacy_history(auth_client):
    response = auth_client.get("/history?limit=20")
    assert response.status_code == 200
    payload = response.get_json()
    assert "history" in payload


def test_logs_api(auth_client):
    response = auth_client.get("/api/v1/logs?limit=20")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True


def test_incidents_endpoint(auth_client):
    response = auth_client.get("/api/v1/incidents?limit=5")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert "incidents" in payload["data"]


def test_decisions_endpoint(auth_client):
    response = auth_client.get("/api/v1/decisions?limit=5")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert "decisions" in payload["data"]


def test_feedback_endpoint(auth_client):
    response = auth_client.get("/api/v1/feedback?limit=5")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert "summary" in payload["data"]


def test_autonomy_status_and_mode_update(auth_client):
    status_response = auth_client.get("/api/v1/autonomy/status")
    assert status_response.status_code == 200
    update_response = auth_client.post("/api/v1/autonomy/mode", json={"mode": "manual"})
    assert update_response.status_code == 200
    refreshed = auth_client.get("/api/v1/autonomy/status")
    payload = refreshed.get_json()
    assert payload["data"]["autonomy"]["mode"] == "manual"


def test_action_validation_missing(auth_client):
    response = auth_client.get("/api/v1/actions/999999/validation")
    assert response.status_code == 404


def test_cluster_overview_endpoint(auth_client):
    response = auth_client.get("/api/v1/cluster/overview")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert "cluster" in payload["data"]
    assert payload["data"]["cluster"]["cluster_name"]


def test_cluster_nodes_endpoint(auth_client):
    response = auth_client.get("/api/v1/cluster/nodes")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert "nodes" in payload["data"]
    assert isinstance(payload["data"]["nodes"], list)


def test_cluster_dependency_map_endpoint(auth_client):
    response = auth_client.get("/api/v1/cluster/dependencies")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert "dependencies" in payload["data"]


def test_cluster_task_create_and_list(auth_client):
    create_response = auth_client.post(
        "/api/v1/cluster/tasks",
        json={"task_type": "refresh_agent_config", "target_node_id": "autoops-node-1", "payload": {"scope": "demo"}},
    )
    assert create_response.status_code == 201
    created = create_response.get_json()
    assert created["ok"] is True
    list_response = auth_client.get("/api/v1/cluster/tasks")
    assert list_response.status_code == 200
    listed = list_response.get_json()
    assert listed["ok"] is True
    assert len(listed["data"]["tasks"]) >= 1


def test_non_admin_cannot_change_autonomy_mode(client):
    client.post("/signup", data={"username": "viewer1", "password": "viewerpass1"}, follow_redirects=True)
    client.post("/login", data={"username": "viewer1", "password": "viewerpass1"}, follow_redirects=True)
    response = client.post("/api/v1/autonomy/mode", json={"mode": "autonomous"})
    assert response.status_code == 403
