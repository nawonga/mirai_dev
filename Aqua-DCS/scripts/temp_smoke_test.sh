#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

PYTHONPATH=src python - <<"PY"
import os

from dcs.drivers.temperature_ds18b20 import Ds18b20Sensor, Ds18b20Config

sensor_id = os.environ.get("AQUA_DS18B20_ID")
s = Ds18b20Sensor(Ds18b20Config(sensor_id=sensor_id))
t = s.read_celsius()
print(f"[temp_smoke_test] DS18B20: {t:.3f} C")
PY
