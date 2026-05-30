"""Export routes (delegates to services.export)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

export_bp = Blueprint("export", __name__)


@export_bp.get("/export")
def export_data():
    params = {
        "sensor": request.args.get("sensor"),
        "from": request.args.get("from"),
        "to": request.args.get("to"),
        "format": request.args.get("format", "csv"),
    }
    # TODO: call services.export
    return jsonify({"status": "pending", "params": params})
