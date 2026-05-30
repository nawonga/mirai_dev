"""기상 캐시 (JSON 파일).

- 원자적 쓰기 (`.tmp` + `os.replace`) — 부분 쓰기 중 읽기 race 회피.
- 메모리에서는 lock 없이 단순 dict 로 보관. FastAPI 단일 프로세스 가정.
- stale 판정: `fetched_at` 으로부터 TTL 초과 또는 다음 KMA 발표 시각 도래.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .kma_client import next_fetch_time

log = logging.getLogger("personal_service.weather.cache")

# 안전 TTL — 발표 주기(3h) 보다 길게 잡아 stale-while-revalidate 동작.
CACHE_TTL = timedelta(hours=3, minutes=30)


@dataclass
class CacheEntry:
    fetched_at: datetime          # 우리가 저장한 시각 (KST)
    base_date: str
    base_time: str
    nx: int
    ny: int
    location_name: str
    hourly: dict[str, dict[str, str]]
    daily: dict[str, dict[str, str]]

    def is_stale(self, now: datetime) -> bool:
        if now - self.fetched_at > CACHE_TTL:
            return True
        # 다음 발표시각이 이미 지나갔으면 stale (즉 새 데이터가 publish 됐을 텐데
        # 우리가 못 받았다는 뜻)
        try:
            nxt = next_fetch_time(self.fetched_at)
        except Exception:
            return True
        return now >= nxt


class WeatherCache:
    """프로세스 내 메모리 보관 + 디스크 영속."""

    def __init__(self, path: Path, location_name: str) -> None:
        self.path = path
        self.location_name = location_name
        self._entry: CacheEntry | None = None
        self._lock = asyncio.Lock()

    def load_from_disk(self) -> CacheEntry | None:
        if not self.path.exists():
            return None
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self._entry = CacheEntry(
                fetched_at=datetime.fromisoformat(raw["fetched_at"]),
                base_date=raw["base_date"],
                base_time=raw["base_time"],
                nx=int(raw["nx"]),
                ny=int(raw["ny"]),
                location_name=raw.get("location_name", self.location_name),
                hourly=raw["hourly"],
                daily=raw.get("daily", {}),
            )
            log.info("캐시 로드 %s base=%s/%s items=%d",
                     self.path, self._entry.base_date, self._entry.base_time,
                     len(self._entry.hourly))
            return self._entry
        except Exception as exc:
            log.warning("캐시 파일 손상 무시: %s", exc)
            return None

    def get(self) -> CacheEntry | None:
        return self._entry

    async def save(self, parsed: dict[str, Any], *, fetched_at: datetime) -> CacheEntry:
        """KMA 파싱 결과를 캐시 엔트리로 저장 (메모리 + 디스크)."""
        entry = CacheEntry(
            fetched_at=fetched_at,
            base_date=parsed["base_date"] or "",
            base_time=parsed["base_time"] or "",
            nx=int(parsed["nx"]),
            ny=int(parsed["ny"]),
            location_name=self.location_name,
            hourly=parsed["hourly"],
            daily=parsed.get("daily", {}),
        )
        async with self._lock:
            self._entry = entry
            await asyncio.to_thread(self._write_atomic, entry)
        log.info("캐시 저장 base=%s/%s hourly=%d daily=%d",
                 entry.base_date, entry.base_time, len(entry.hourly), len(entry.daily))
        return entry

    def _write_atomic(self, entry: CacheEntry) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "fetched_at": entry.fetched_at.isoformat(timespec="seconds"),
            "base_date": entry.base_date,
            "base_time": entry.base_time,
            "nx": entry.nx,
            "ny": entry.ny,
            "location_name": entry.location_name,
            "hourly": entry.hourly,
            "daily": entry.daily,
        }
        fd, tmp = tempfile.mkstemp(prefix=".weather_cache_", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fp:
                json.dump(payload, fp, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise


def resolve_cache_path(raw: str, service_root: Path) -> Path:
    p = Path(raw)
    if not p.is_absolute():
        p = service_root / p
    return p
