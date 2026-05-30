"""`get_weather` operation — 캐시에서 읽고 자연어 message 생성."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from ..weather.cache import WeatherCache
from ..weather.formatter import format_weather


def execute(
    params: dict[str, Any],
    tz: ZoneInfo,
    *,
    cache: WeatherCache,
    service_key_set: bool,
) -> tuple[bool, str, dict[str, Any]]:
    """Return `(ok, message, data_payload)`.

    Params:
        when: "now" | "today" | "tomorrow" (기본 "now").
    """
    when = params.get("when", "now")
    if when not in {"now", "today", "tomorrow"}:
        raise ValueError(f"unsupported when: {when!r}")

    entry = cache.get()
    if entry is None:
        msg = (
            "날씨 서비스가 아직 설정되지 않았어요."
            if not service_key_set
            else "아직 날씨 데이터를 받아오지 못했어요. 잠시 후 다시 시도해주세요."
        )
        return False, msg, {
            "when": when,
            "cache": {"available": False, "service_key_set": service_key_set},
        }

    now = datetime.now(tz)
    stale = entry.is_stale(now)
    message, extra = format_weather(entry, when=when, now=now)

    if stale:
        message = "잠시 통신이 어려워 마지막으로 받은 정보로 알려드려요. " + message

    data: dict[str, Any] = {
        "when": when,
        "cache": {
            "available": True,
            "stale": stale,
            "fetched_at": entry.fetched_at.isoformat(timespec="seconds"),
            "base_date": entry.base_date,
            "base_time": entry.base_time,
            "nx": entry.nx,
            "ny": entry.ny,
            "location_name": entry.location_name,
        },
    }
    data.update(extra)
    return True, message, data
