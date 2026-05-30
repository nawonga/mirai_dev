"""Collector loop — samples every 5 s, flushes 1-min trimmed-mean to DB.

Aggregation strategy
--------------------
* Sample interval : SAMPLE_SEC  (default 5 s)
* Flush interval  : FLUSH_SEC   (default 60 s)
* Aggregation     : trimmed mean — drop the single highest and single lowest
                    value before averaging.  Requires ≥ 3 samples; falls back
                    to plain mean for 2 samples, or the single value for 1.
* note field      : JSON with agg metadata so the strategy is self-documenting
                    in the DB.

Live export
-----------
Every sample cycle the latest raw values are written to LIVE_JSON_PATH
(default /run/aqua-dcs/latest.json) so the Flask API can serve 5-second
live readings without any DB writes.
"""

from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from dcs.drivers.temperature_ds18b20 import Ds18b20Config, Ds18b20Error, Ds18b20Sensor
from dcs.storage.sqlite import Measurement, init_db, insert_measurement

# ── tunables ──────────────────────────────────────────────────────────────────
SAMPLE_SEC: int = int(os.environ.get("AQUA_SAMPLE_SEC", "5"))
FLUSH_SEC: int = int(os.environ.get("AQUA_FLUSH_SEC", "60"))
LIVE_JSON_PATH: Path = Path(os.environ.get("AQUA_LIVE_JSON", "/run/aqua-dcs/latest.json"))

SENSORS: list[tuple[str, str]] = [
    ("temperature", "C"),
    ("salinity", "ppt"),
    ("ph", "pH"),
    ("light", "lux"),
]

# Dummy ranges for sensors without real hardware yet
_DUMMY_RANGES: dict[str, tuple[float, float]] = {
    "salinity": (30.0, 35.0),
    "ph": (7.9, 8.3),
    "light": (120.0, 180.0),
}


# ── helpers ───────────────────────────────────────────────────────────────────

def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def trimmed_mean(values: list[float]) -> tuple[float, dict]:
    """Return (mean, meta) where meta carries aggregation details."""
    n = len(values)
    if n == 0:
        raise ValueError("empty sample list")
    if n <= 2:
        avg = sum(values) / n
        return avg, {"agg": "mean", "samples": n, "excluded": 0,
                     "min": min(values), "max": max(values)}
    # drop one min and one max
    sorted_v = sorted(values)
    trimmed = sorted_v[1:-1]
    avg = sum(trimmed) / len(trimmed)
    return avg, {
        "agg": "trimmed_mean",
        "samples": n,
        "excluded": 2,
        "min": sorted_v[0],
        "max": sorted_v[-1],
        "trimmed_min": trimmed[0],
        "trimmed_max": trimmed[-1],
    }


def write_live(snapshot: dict) -> None:
    """Atomically write live snapshot to LIVE_JSON_PATH (tmpfs-safe)."""
    try:
        LIVE_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = LIVE_JSON_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(snapshot), encoding="utf-8")
        tmp.rename(LIVE_JSON_PATH)
    except Exception as e:
        print(f"[collector] live write error: {e}")


# ── main ──────────────────────────────────────────────────────────────────────

def main(sample_sec: int = SAMPLE_SEC, flush_sec: int = FLUSH_SEC) -> None:
    init_db()

    ds18b20_id = os.environ.get("AQUA_DS18B20_ID")
    temp_sensor = Ds18b20Sensor(Ds18b20Config(sensor_id=ds18b20_id))

    # in-memory buffer: sensor_name -> list[float]
    buffer: dict[str, list[float]] = defaultdict(list)
    last_flush = time.monotonic()

    print(
        f"[collector] started — sample={sample_sec}s  flush={flush_sec}s  "
        f"ds18b20_id={ds18b20_id or 'auto'}  live={LIVE_JSON_PATH}"
    )

    while True:
        import random  # local import to keep top-level clean

        ts = utc_now()
        live_snapshot: dict = {"ts_utc": ts, "sensors": {}}

        # ── sample ────────────────────────────────────────────────────────────
        for sensor, unit in SENSORS:
            if sensor == "temperature":
                try:
                    val = temp_sensor.read_celsius()
                    buffer[sensor].append(val)
                    live_snapshot["sensors"][sensor] = {
                        "value": round(val, 4), "unit": unit,
                        "status": "OK", "source": "sensor",
                    }
                except Ds18b20Error as e:
                    print(f"[collector] DS18B20 read error: {e}")
                    # do NOT append — bad read is simply skipped
                    live_snapshot["sensors"][sensor] = {
                        "value": None, "unit": unit,
                        "status": "ERROR", "source": "sensor",
                    }
            else:
                lo, hi = _DUMMY_RANGES[sensor]
                val = random.uniform(lo, hi)
                buffer[sensor].append(val)
                live_snapshot["sensors"][sensor] = {
                    "value": round(val, 4), "unit": unit,
                    "status": "OK", "source": "dummy",
                }

        # write live snapshot every sample cycle (5 s) — no DB write
        write_live(live_snapshot)

        # ── flush? ────────────────────────────────────────────────────────────
        now = time.monotonic()
        if now - last_flush >= flush_sec:
            flush_ts = utc_now()
            for sensor, unit in SENSORS:
                samples = buffer.pop(sensor, [])
                if not samples:
                    print(f"[collector] no samples for {sensor}, skipping flush")
                    continue
                avg, meta = trimmed_mean(samples)
                meta["window_sec"] = flush_sec
                # Persist whether this row came from a real sensor or dummy source.
                # NOTE: Today, only temperature is real (DS18B20); others are dummy.
                meas_source = "sensor" if sensor == "temperature" else "dummy"
                measurement = Measurement(
                    ts_utc=flush_ts,
                    sensor=sensor,
                    value=round(avg, 4),
                    unit=unit,
                    status="OK",
                    source=meas_source,
                    raw_value=round(avg, 4),
                    note=json.dumps(meta, separators=(",", ":")),
                )
                insert_measurement(measurement)
                print(
                    f"[collector] flush {sensor}: {measurement.value} {unit} "
                    f"(n={meta['samples']} excl={meta['excluded']}) @ {flush_ts}"
                )
            last_flush = now

        time.sleep(sample_sec)


if __name__ == "__main__":
    main()
