def test_login_page_loads(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Sign in" in response.data


def test_login_logout_flow(client):
    login = client.post("/login", data={"username": "admin", "password": "admin123!"}, follow_redirects=True)
    assert login.status_code == 200
    assert b"Production-grade AIOps control plane" in login.data

    logout = client.get("/logout", follow_redirects=True)
    assert logout.status_code == 200
    assert b"Sign in" in logout.data
