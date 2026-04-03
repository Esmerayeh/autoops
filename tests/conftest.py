from __future__ import annotations

import pytest

from autoops import create_app
from autoops.extensions import db
from autoops.services.bootstrap import ensure_seed_data


@pytest.fixture()
def app():
    app = create_app(
        "testing",
        overrides={
            "DEFAULT_ADMIN_USERNAME": "admin",
            "DEFAULT_ADMIN_PASSWORD": "admin123!",
        },
    )
    with app.app_context():
        db.drop_all()
        db.create_all()
        ensure_seed_data()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_client(client):
    client.post("/login", data={"username": "admin", "password": "admin123!"}, follow_redirects=True)
    return client
