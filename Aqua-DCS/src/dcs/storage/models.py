"""SQLite schema definitions for aqua-dcs."""

MEASUREMENTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS measurements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts_utc TEXT NOT NULL,
  sensor TEXT NOT NULL,
  value REAL NOT NULL,
  unit TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'OK',
  source TEXT DEFAULT 'collector',
  raw_value REAL,
  note TEXT
);
"""

SENSORS_SCHEMA = """
CREATE TABLE IF NOT EXISTS sensors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  model TEXT,
  location TEXT,
  enabled INTEGER NOT NULL DEFAULT 1,
  calibration_version TEXT,
  installed_at TEXT,
  note TEXT
);
"""

CALIBRATION_LOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS calibration_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts_utc TEXT NOT NULL,
  sensor TEXT NOT NULL,
  method TEXT,
  params TEXT,
  note TEXT
);
"""

SYSTEM_EVENTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS system_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts_utc TEXT NOT NULL,
  level TEXT NOT NULL,
  source TEXT NOT NULL,
  message TEXT NOT NULL,
  meta TEXT
);
"""

EVENTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts_utc TEXT NOT NULL,
  category TEXT NOT NULL,      -- alarm / manual / maintenance
  level TEXT NOT NULL,         -- INFO / WARN / ERROR
  title TEXT NOT NULL,
  message TEXT,
  acknowledged INTEGER NOT NULL DEFAULT 0,
  source TEXT DEFAULT 'services',
  meta TEXT
);
"""

REPORTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts_utc TEXT NOT NULL,
  period TEXT NOT NULL,         -- weekly / monthly
  title TEXT NOT NULL,
  summary TEXT,
  payload TEXT                 -- JSON
);
"""

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_measurements_ts ON measurements(ts_utc);",
    "CREATE INDEX IF NOT EXISTS idx_measurements_sensor_ts ON measurements(sensor, ts_utc);",
]

ALL_SCHEMAS = [
    MEASUREMENTS_SCHEMA,
    SENSORS_SCHEMA,
    CALIBRATION_LOG_SCHEMA,
    SYSTEM_EVENTS_SCHEMA,
    EVENTS_SCHEMA,
    REPORTS_SCHEMA,
]
