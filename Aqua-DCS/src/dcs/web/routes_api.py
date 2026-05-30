"""API routes for aqua-dcs."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Blueprint, jsonify, request

from dcs.storage.sqlite import fetch_history, fetch_latest

api_bp = Blueprint("api", __name__)

LIVE_JSON_PATH = Path(os.environ.get("AQUA_LIVE_JSON", "/run/aqua-dcs/latest.json"))


# ── existing endpoints ────────────────────────────────────────────────────────

@api_bp.get("/latest")
def latest():
    sensor = request.args.get("sensor")
    return jsonify(fetch_latest(sensor))


@api_bp.get("/history")
def history():
    sensor = request.args.get("sensor")
    if not sensor:
        return jsonify({"error": "sensor is required"}), 400

    from_ts = request.args.get("from")
    to_ts = request.args.get("to")
    limit = int(request.args.get("limit", 500))

    return jsonify(fetch_history(sensor, from_ts=from_ts, to_ts=to_ts, limit=limit))


@api_bp.get("/recent")
def recent():
    """Return the most recent N minutes of data for a sensor."""
    sensor = request.args.get("sensor")
    if not sensor:
        return jsonify({"error": "sensor is required"}), 400

    minutes = int(request.args.get("minutes", 10))
    limit = int(request.args.get("limit", 500))

    from_dt = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    from_ts = from_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    rows = fetch_history(sensor, from_ts=from_ts, limit=limit)
    return jsonify(rows)


@api_bp.get("/recent/all")
def recent_all():
    """Return recent data for ALL sensors in one call.

    Response: { "temperature": [...], "salinity": [...], ... }
    """
    minutes = int(request.args.get("minutes", 10))
    limit = int(request.args.get("limit", 500))

    from_dt = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    from_ts = from_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    sensors = ["temperature", "salinity", "ph", "light"]
    result = {}
    for s in sensors:
        result[s] = fetch_history(s, from_ts=from_ts, limit=limit)

    return jsonify(result)


@api_bp.get("/history/all")
def history_all():
    """Return history data for ALL sensors in one call.

    Query params:
      from: ISO8601 UTC string (inclusive) e.g. 2026-02-18T12:00:00Z
      to:   ISO8601 UTC string (inclusive)
      limit: max rows per-sensor

    Response: { "temperature": [...], "salinity": [...], ... }
    """
    from_ts = request.args.get("from")
    to_ts = request.args.get("to")
    if not from_ts or not to_ts:
        return jsonify({"error": "from and to are required"}), 400

    limit = int(request.args.get("limit", 2000))

    sensors = ["temperature", "salinity", "ph", "light"]
    result = {}
    for s in sensors:
        result[s] = fetch_history(s, from_ts=from_ts, to_ts=to_ts, limit=limit)

    return jsonify(result)


# ── live endpoint (5-second, no DB) ──────────────────────────────────────────

@api_bp.get("/live/latest")
def live_latest():
    """Return the most recent raw sample written by the collector (5-second cadence).

    Reads from LIVE_JSON_PATH (default /run/aqua-dcs/latest.json) which is
    written by the collector every sample cycle without touching the DB.

    Response shape:
      {
        "ts_utc": "2026-02-18T12:34:56Z",
        "sensors": {
          "temperature": {"value": 23.75, "unit": "C", "status": "OK"},
          ...
        }
      }
    """
    if not LIVE_JSON_PATH.exists():
        return jsonify({"error": "live data not available yet"}), 503

    try:
        data = json.loads(LIVE_JSON_PATH.read_text(encoding="utf-8"))
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
