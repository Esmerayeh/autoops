def test_health_requires_auth(client):
    response = client.get("/api/v1/health")
    assert response.status_code in {302, 401}


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


def test_action_validation_missing(auth_client):
    response = auth_client.get("/api/v1/actions/999999/validation")
    assert response.status_code == 404
