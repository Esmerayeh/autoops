"""Authentication routes and session security."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from autoops.extensions import db, limiter
from autoops.models import LoginAudit, User

auth_bp = Blueprint("auth", __name__)


def audit_login(username: str, event_type: str, success: bool, details: dict | None = None) -> None:
    record = LoginAudit(
        username=username or "<empty>",
        event_type=event_type,
        success=success,
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
        user_agent=(request.headers.get("User-Agent") or "")[:255],
        details=details or {},
    )
    db.session.add(record)
    db.session.commit()


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if not current_app.config["ENABLE_SIGNUP"]:
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if len(username) < 3:
            return render_template("signup.html", error="Username must be at least 3 characters.")
        if len(password) < 8:
            return render_template("signup.html", error="Password must be at least 8 characters.")
        if User.query.filter_by(username=username).first():
            return render_template("signup.html", error="User already exists.")

        user = User(username=username, password_hash=generate_password_hash(password), role="viewer")
        db.session.add(user)
        db.session.commit()
        audit_login(username, "signup", True, {"role": "viewer"})
        flash("Account created. You can now sign in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("signup.html", error=None)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit(lambda: current_app.config["LOGIN_RATE_LIMIT"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("ui.dashboard"))

    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = User.query.filter_by(username=username).first()

        if not user:
            audit_login(username, "login", False, {"reason": "user_not_found"})
            error = "Invalid credentials."
        elif user.locked_until and user.locked_until > datetime.now(timezone.utc):
            audit_login(username, "login", False, {"reason": "account_locked"})
            error = "Account temporarily locked. Try again later."
        elif not check_password_hash(user.password_hash, password):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= current_app.config["MAX_FAILED_LOGINS"]:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=current_app.config["ACCOUNT_LOCKOUT_MINUTES"])
            db.session.commit()
            audit_login(username, "login", False, {"reason": "bad_password", "failed_login_attempts": user.failed_login_attempts})
            error = "Invalid credentials."
        else:
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login_at = datetime.now(timezone.utc)
            db.session.commit()
            login_user(user)
            audit_login(username, "login", True)
            next_url = request.args.get("next") or url_for("ui.dashboard")
            return redirect(next_url)

    return render_template("login.html", error=error)


@auth_bp.route("/logout")
@login_required
def logout():
    username = current_user.username
    logout_user()
    audit_login(username, "logout", True)
    return redirect(url_for("auth.login"))
