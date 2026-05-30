"""Control request routes (requests only, execution via services.control)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

control_bp = Blueprint("control", __name__)


@control_bp.post("/control/request")
def request_control():
    payload = request.get_json(silent=True) or {}
    # TODO: forward to services.control (queue/log)
    return jsonify({"status": "accepted", "payload": payload})
