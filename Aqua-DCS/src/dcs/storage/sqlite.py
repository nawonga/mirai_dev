"""SQLite helpers for aqua-dcs."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from . import models

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "aqua.db"


@dataclass(frozen=True)
class Measurement:
    ts_utc: str
    sensor: str
    value: float
    unit: str
    status: str = "OK"
    source: str = "collector"
    raw_value: Optional[float] = None
    note: Optional[str] = None


def _ensure_parent_dir(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)


def connect(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    _ensure_parent_dir(path)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_session(db_path: Path | str = DEFAULT_DB_PATH) -> Iterable[sqlite3.Connection]:
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path | str = DEFAULT_DB_PATH) -> None:
    with db_session(db_path) as conn:
        for schema in models.ALL_SCHEMAS:
            conn.execute(schema)
        for index in models.INDEXES:
            conn.execute(index)


def insert_measurement(
    measurement: Measurement,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> int:
    query = (
        "INSERT INTO measurements (ts_utc, sensor, value, unit, status, source, raw_value, note) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    )
    with db_session(db_path) as conn:
        cursor = conn.execute(
            query,
            (
                measurement.ts_utc,
                measurement.sensor,
                measurement.value,
                measurement.unit,
                measurement.status,
                measurement.source,
                measurement.raw_value,
                measurement.note,
            ),
        )
        return int(cursor.lastrowid)


def fetch_latest(sensor: Optional[str] = None, db_path: Path | str = DEFAULT_DB_PATH):
    if sensor:
        query = "SELECT * FROM measurements WHERE sensor = ? ORDER BY ts_utc DESC LIMIT 1"
        params = (sensor,)
    else:
        query = "SELECT * FROM measurements ORDER BY ts_utc DESC LIMIT 1"
        params = ()
    with db_session(db_path) as conn:
        row = conn.execute(query, params).fetchone()
    return dict(row) if row else None


def fetch_history(
    sensor: str,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
    limit: int = 500,
    db_path: Path | str = DEFAULT_DB_PATH,
):
    conditions = ["sensor = ?"]
    params = [sensor]

    if from_ts:
        conditions.append("ts_utc >= ?")
        params.append(from_ts)
    if to_ts:
        conditions.append("ts_utc <= ?")
        params.append(to_ts)

    where_clause = " AND ".join(conditions)
    query = (
        f"SELECT * FROM measurements WHERE {where_clause} "
        "ORDER BY ts_utc ASC LIMIT ?"
    )
    params.append(limit)

    with db_session(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]
