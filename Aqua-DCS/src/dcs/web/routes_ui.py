"""UI routes for aqua-dcs."""

from __future__ import annotations

from flask import Blueprint, render_template

ui_bp = Blueprint("ui", __name__)


@ui_bp.get("/")
def dashboard():
    return render_template("dashboard.html")
