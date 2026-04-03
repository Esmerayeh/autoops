"""Bootstrap helpers for initial data."""

from __future__ import annotations

from werkzeug.security import generate_password_hash

from autoops.extensions import db
from autoops.models import User


def ensure_seed_data() -> None:
    """Create the default admin user when the database is empty."""
    from flask import current_app

    username = current_app.config["DEFAULT_ADMIN_USERNAME"]
    password = current_app.config["DEFAULT_ADMIN_PASSWORD"]
    role = current_app.config["DEFAULT_ADMIN_ROLE"]

    if not User.query.filter_by(username=username).first():
        admin = User(
            username=username,
            password_hash=generate_password_hash(password),
            role=role,
        )
        db.session.add(admin)
        db.session.commit()
