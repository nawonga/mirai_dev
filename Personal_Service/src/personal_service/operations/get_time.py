"""`get_time` operation — 현재 시각/날짜/요일 + 상대 시간 (OPERATING.md §3.4)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

_WEEKDAYS_KO = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]


def _format_time_ko(dt: datetime) -> str:
    hour = dt.hour
    if hour == 0:
        period, h12 = "오전", 12
    elif hour < 12:
        period, h12 = "오전", hour
    elif hour == 12:
        period, h12 = "오후", 12
    else:
        period, h12 = "오후", hour - 12
    return f"{period} {h12}시 {dt.minute}분"


def _format_date_ko(dt: datetime) -> str:
    return f"{dt.year}년 {dt.month}월 {dt.day}일"


def _build_message(dt: datetime, field: str, offset_days: int) -> str:
    when = "오늘은" if offset_days == 0 else f"{offset_days}일 뒤는"
    if field == "time":
        if offset_days == 0:
            return f"지금은 {_format_time_ko(dt)}이에요."
        return f"{when} {_format_date_ko(dt)} {_format_time_ko(dt)}이에요."
    if field == "date":
        return f"{when} {_format_date_ko(dt)}이에요."
    if field == "weekday":
        return f"{when} {_WEEKDAYS_KO[dt.weekday()]}이에요."
    return (
        f"{when} {_format_date_ko(dt)} "
        f"{_WEEKDAYS_KO[dt.weekday()]}, {_format_time_ko(dt)}이에요."
    )


def execute(params: dict[str, Any], tz: ZoneInfo) -> tuple[str, dict[str, Any]]:
    """Return `(message, data_payload)`.

    Params:
        field: "time" | "date" | "weekday" | "all" (기본 "all")
        offset_days: 상대 시간 일수 (기본 0). 양수는 미래, 음수는 과거.
    """
    field = params.get("field", "all")
    if field not in {"time", "date", "weekday", "all"}:
        raise ValueError(f"unsupported field: {field!r}")

    offset_days = int(params.get("offset_days", 0))
    now = datetime.now(tz)
    target = now + timedelta(days=offset_days)

    message = _build_message(target, field, offset_days)
    data = {
        "now": now.isoformat(timespec="seconds"),
        "target": target.isoformat(timespec="seconds"),
        "field": field,
        "offset_days": offset_days,
        "weekday": _WEEKDAYS_KO[target.weekday()],
        "timezone": str(tz),
    }
    return message, data
