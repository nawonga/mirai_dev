"""캐시 → 한국어 자연어 message + 구조화 data.

`when` ∈ {"now", "today", "tomorrow"} 만 지원.

문장 조립 방식:
- 각 fact 를 **완결 문장 (마침표 포함)** 으로 만들어 ` ` 로 join.
- 자동 종결어 suffix 를 붙이지 않아 어미 중복 (예: "있어요이에요") 방지.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .cache import CacheEntry

SKY = {"1": "맑음", "3": "구름 많음", "4": "흐림"}
PTY = {"0": None, "1": "비", "2": "비/눈", "3": "눈", "4": "소나기"}


def _bucket_key(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H00")


def _pick_nearest_bucket(entry: CacheEntry, now: datetime) -> tuple[str, dict[str, str]] | None:
    target = _bucket_key(now.replace(minute=0, second=0, microsecond=0))
    if target in entry.hourly:
        return target, entry.hourly[target]
    future = sorted(k for k in entry.hourly if k >= target)
    if future:
        return future[0], entry.hourly[future[0]]
    past = sorted(entry.hourly.keys())
    if past:
        return past[-1], entry.hourly[past[-1]]
    return None


def _buckets_for_date(entry: CacheEntry, yyyymmdd: str) -> list[tuple[str, dict[str, str]]]:
    return sorted((k, v) for k, v in entry.hourly.items() if k.startswith(yyyymmdd + "T"))


def _int_or_none(v: str | None) -> int | None:
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def _format_now(entry: CacheEntry, now: datetime) -> tuple[str, dict[str, Any]]:
    pick = _pick_nearest_bucket(entry, now)
    if pick is None:
        return "지금 시각의 예보 데이터를 찾을 수 없어요.", {"error": "no_bucket"}
    bucket_key, b = pick

    tmp = _int_or_none(b.get("TMP"))
    sky_label = SKY.get(b.get("SKY", ""))
    pty_label = PTY.get(b.get("PTY", "0"))
    pop = _int_or_none(b.get("POP"))
    reh = _int_or_none(b.get("REH"))

    sentences: list[str] = []
    if tmp is not None:
        sentences.append(f"현재 {entry.location_name} 기온은 {tmp}도예요.")
    else:
        sentences.append(f"현재 {entry.location_name} 날씨를 알려드릴게요.")
    if sky_label:
        sentences.append(f"하늘은 {sky_label}이에요.")
    if pty_label:
        sentences.append(f"지금 {pty_label}이 내리고 있어요.")
    elif pop is not None:
        if pop >= 30:
            sentences.append(f"강수 확률은 {pop}%예요.")
        # 30 미만은 굳이 멘트하지 않음 (간결성)
    if reh is not None and not pty_label:
        sentences.append(f"습도는 {reh}%예요.")

    return " ".join(sentences), {"bucket": bucket_key, "fields": b}


def _format_day(entry: CacheEntry, when: str, now: datetime) -> tuple[str, dict[str, Any]]:
    target_date = now.date() if when == "today" else (now + timedelta(days=1)).date()
    yyyymmdd = target_date.strftime("%Y%m%d")
    buckets = _buckets_for_date(entry, yyyymmdd)
    if not buckets:
        when_label = "오늘" if when == "today" else "내일"
        return f"{when_label} 예보 데이터를 찾을 수 없어요.", {"error": "no_bucket", "date": yyyymmdd}

    temps = [t for t in (_int_or_none(b.get("TMP")) for _, b in buckets) if t is not None]
    pops = [p for p in (_int_or_none(b.get("POP")) for _, b in buckets) if p is not None]
    ptys = {PTY.get(b.get("PTY", "0")) for _, b in buckets} - {None}
    skies = [s for s in (SKY.get(b.get("SKY", ""), None) for _, b in buckets) if s]

    daily = entry.daily.get(yyyymmdd, {})
    tmn = _int_or_none(daily.get("TMN")) if daily.get("TMN") else (min(temps) if temps else None)
    tmx = _int_or_none(daily.get("TMX")) if daily.get("TMX") else (max(temps) if temps else None)

    when_label = "오늘" if when == "today" else "내일"
    dominant = max(set(skies), key=skies.count) if skies else None
    pop_max = max(pops) if pops else None

    sentences: list[str] = [f"{when_label} {entry.location_name} 날씨를 알려드릴게요."]
    if dominant:
        sentences.append(f"하늘은 전반적으로 {dominant}이에요.")
    if tmn is not None and tmx is not None:
        sentences.append(f"최저 {tmn}도, 최고 {tmx}도예요.")
    if ptys:
        sentences.append(f"{'·'.join(sorted(ptys))} 예보가 있어요.")
    elif pop_max is not None and pop_max >= 30:
        sentences.append(f"강수 확률은 최대 {pop_max}%예요.")
    else:
        sentences.append("강수 가능성은 낮아요.")

    return " ".join(sentences), {
        "date": yyyymmdd,
        "temp_min": tmn,
        "temp_max": tmx,
        "pop_max": pop_max,
        "pty_seen": sorted(ptys) if ptys else [],
        "sky_dominant": dominant,
        "buckets": len(buckets),
    }


def format_weather(entry: CacheEntry, *, when: str, now: datetime) -> tuple[str, dict[str, Any]]:
    if when == "now":
        return _format_now(entry, now)
    if when in ("today", "tomorrow"):
        return _format_day(entry, when, now)
    raise ValueError(f"unsupported when: {when!r}")
