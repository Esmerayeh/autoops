"""Application factory for AutoOps AI."""

from __future__ import annotations

import logging
import os
from typing import Any

from flask import Flask, jsonify, render_template, request

from autoops.api.routes import api_bp, legacy_bp
from autoops.auth.routes import auth_bp
from autoops.config import config_by_name
from autoops.extensions import csrf, db, limiter, login_manager, migrate
from autoops.models import User
from autoops.services.bootstrap import ensure_seed_data
from autoops.services.runtime import runtime_manager
from autoops.ui.routes import ui_bp
from autoops.utils.logging import configure_logging
from autoops.utils.responses import error_response
from autoops.utils.security import apply_security_headers


def create_app(config_name: str | None = None, overrides: dict[str, Any] | None = None) -> Flask:
    """Create and configure the Flask application."""
    config_name = config_name or os.getenv("AUTOOPS_ENV", "development")
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        static_url_path="/static",
    )
    app.config.from_object(config_by_name[config_name])
    if overrides:
        app.config.update(overrides)

    configure_logging(app)
    register_extensions(app)
    register_blueprints(app)
    register_hooks(app)
    register_error_handlers(app)

    with app.app_context():
        db.create_all()
        ensure_seed_data()
        runtime_manager.start(app)

    return app


def register_extensions(app: Flask) -> None:
    """Initialize Flask extensions."""
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)


def register_blueprints(app: Flask) -> None:
    """Register HTTP blueprints."""
    app.register_blueprint(auth_bp)
    app.register_blueprint(ui_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(legacy_bp)


def register_hooks(app: Flask) -> None:
    """Register lifecycle and request hooks."""

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return db.session.get(User, int(user_id))

    @app.before_request
    def before_request() -> None:
        runtime_manager.mark_request_start()

    @app.after_request
    def after_request(response):  # type: ignore[no-untyped-def]
        runtime_manager.record_request(response.status_code)
        apply_security_headers(response, app.config)
        return response


def register_error_handlers(app: Flask) -> None:
    """Register JSON- and page-friendly error handlers."""

    @app.errorhandler(400)
    def bad_request(error):  # type: ignore[no-untyped-def]
        if request.path.startswith("/api/") or request.path.startswith("/stats"):
            return jsonify(error_response("bad_request", "Invalid request.", 400)), 400
        return render_template("errors/400.html"), 400

    @app.errorhandler(401)
    def unauthorized(error):  # type: ignore[no-untyped-def]
        if request.path.startswith("/api/"):
            return jsonify(error_response("unauthorized", "Authentication required.", 401)), 401
        return render_template("errors/401.html"), 401

    @app.errorhandler(403)
    def forbidden(error):  # type: ignore[no-untyped-def]
        if request.path.startswith("/api/"):
            return jsonify(error_response("forbidden", "You are not allowed to perform this action.", 403)), 403
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):  # type: ignore[no-untyped-def]
        if request.path.startswith("/api/"):
            return jsonify(error_response("not_found", "The requested resource was not found.", 404)), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(429)
    def rate_limited(error):  # type: ignore[no-untyped-def]
        if request.path.startswith("/api/") or request.path.startswith("/login"):
            return jsonify(error_response("rate_limited", "Too many requests.", 429)), 429
        return render_template("errors/429.html"), 429

    @app.errorhandler(Exception)
    def internal_error(error):  # type: ignore[no-untyped-def]
        logging.exception("Unhandled application error: %s", error)
        if request.path.startswith("/api/"):
            return jsonify(error_response("internal_error", "An internal error occurred.", 500)), 500
        return render_template("errors/500.html"), 500
