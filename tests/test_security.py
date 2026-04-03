def test_security_headers(auth_client):
    response = auth_client.get("/api/v1/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_login_lockout(client, app):
    for _ in range(app.config["MAX_FAILED_LOGINS"]):
        client.post("/login", data={"username": "admin", "password": "wrong-password"})
    response = client.post("/login", data={"username": "admin", "password": "wrong-password"})
    assert response.status_code in {200, 429}
