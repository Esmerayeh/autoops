"""Dashboard UI routes."""

from flask import Blueprint, render_template
from flask_login import current_user, login_required

ui_bp = Blueprint("ui", __name__)


@ui_bp.route("/")
@login_required
def dashboard():
    return render_template("index.html", current_user=current_user)
