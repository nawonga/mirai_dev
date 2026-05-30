
"""DS18B20 temperature sensor (1-Wire) driver.

We rely on the Linux kernel 1-wire subsystem exposing the sensor under sysfs:

  /sys/bus/w1/devices/28-xxxx/w1_slave

The file contains two lines; the first includes CRC status (YES/NO),
the second includes a `t=<millidegC>` value.

This module provides a small, dependency-free driver so Aqua-DCS can remain
local-first and lightweight.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path


W1_SYSFS_ROOT = Path("/sys/bus/w1/devices")


class Ds18b20Error(RuntimeError):
    pass


@dataclass(frozen=True)
class Ds18b20Config:
    sysfs_root: Path = W1_SYSFS_ROOT
    sensor_id: str | None = None  # e.g. "28-000000833080"
    retries: int = 3
    retry_sleep_seconds: float = 0.2


class Ds18b20Sensor:
    def __init__(self, cfg: Ds18b20Config | None = None):
        self.cfg = cfg or Ds18b20Config()

    def _discover_sensor_id(self) -> str:
        devices_dir = self.cfg.sysfs_root
        if not devices_dir.exists():
            raise Ds18b20Error(
                f"1-Wire sysfs not found: {devices_dir}. "
                "Check /boot/firmware/config.txt dtoverlay=w1-gpio-..., and reboot."
            )

        matches = sorted(p.name for p in devices_dir.glob("28-*") if p.is_dir())
        if not matches:
            raise Ds18b20Error(
                f"No DS18B20 found under {devices_dir}/28-*"  # pragma: no cover
            )
        return matches[0]

    def detected_sensor_ids(self) -> list[str]:
        """Return all detected DS18B20 ids under sysfs."""
        devices_dir = self.cfg.sysfs_root
        if not devices_dir.exists():
            return []
        return sorted(p.name for p in devices_dir.glob("28-*") if p.is_dir())

    def _w1_slave_path(self) -> Path:
        sensor_id = self.cfg.sensor_id or self._discover_sensor_id()
        return self.cfg.sysfs_root / sensor_id / "w1_slave"

    def read_celsius(self) -> float:
        """Return temperature in Celsius.

        Retries when CRC is NO.
        """

        path = self._w1_slave_path()
        last_detail = ""

        for attempt in range(1, int(self.cfg.retries) + 1):
            try:
                raw = path.read_text(encoding="utf-8", errors="ignore")
            except FileNotFoundError as e:
                raise Ds18b20Error(f"w1_slave not found: {path}") from e

            lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
            if len(lines) < 2:
                last_detail = raw
            else:
                crc_ok = lines[0].endswith("YES")
                if not crc_ok:
                    last_detail = lines[0]
                else:
                    # parse t=21812 (millideg C)
                    idx = lines[1].find("t=")
                    if idx >= 0:
                        milli = int(lines[1][idx + 2 :].strip())
                        return milli / 1000.0
                    last_detail = lines[1]

            if attempt < self.cfg.retries:
                time.sleep(float(self.cfg.retry_sleep_seconds))

        raise Ds18b20Error(f"DS18B20 read failed after retries. detail={last_detail!r}")

