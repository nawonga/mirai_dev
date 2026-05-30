"""Event routes for manual logging and list view."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

events_bp = Blueprint("events", __name__)


@events_bp.get("/events")
def list_events():
    # TODO: read from storage
    return jsonify([])


@events_bp.post("/events")
def create_event():
    payload = request.get_json(silent=True) or {}
    # TODO: write via services.alarms or storage
    return jsonify({"status": "created", "payload": payload})
