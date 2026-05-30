"""자연어 → 도메인 명령 라우터 (룰베이스).

Gemini fallback 도입 전 단계의 단순 매칭. 결정적·고속·고신뢰 케이스만 잡고,
모호/우회 발화는 Gemini 가 처리한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RoutedIntent:
    intent: str
    domain: str   # personal_service | home_iot | aqua_dcs | none
    operation: str | None
    # Home_IOT 라우팅에서는 params 대신 device_id/action 을 따로 들고감
    params: dict[str, Any] = field(default_factory=dict)
    device_id: str | None = None
    action: str | None = None
    confidence: float = 0.0
    entities: dict[str, Any] = field(default_factory=dict)


def _normalize(text: str) -> str:
    return re.sub(r"[^\w가-힣]", "", text or "").lower()


# ---------------- Personal_Service ----------------

def _weather_when(low: str) -> str:
    if "내일" in low or "낼" in low:
        return "tomorrow"
    if "오늘" in low:
        return "today"
    if "모레" in low:
        return "tomorrow"   # 단기예보 한계 — Gemini 가 가능하면 더 정교히 처리
    return "now"


def _is_weather(low: str) -> bool:
    return any(k in low for k in ("날씨", "기온", "온도", "비와", "비올", "비온", "더워", "추워", "맑", "흐림", "흐려"))


def _is_time(low: str) -> bool:
    return ("몇시" in low) or ("시간" in low and any(k in low for k in ("지금", "알려", "뭐", "몇")))


def _is_reminder(low: str) -> bool:
    return any(k in low for k in ("알람", "리마인더", "일정", "예약"))


# ---------------- Home_IOT ----------------

# 액션 키워드 (정규형 텍스트 기준 — _normalize 후 공백 제거 형태)
_TURN_ON_KEYS = ("켜줘", "켜라", "켜자", "켜")
_TURN_OFF_KEYS = ("꺼줘", "꺼라", "꺼자", "꺼", "끄세요", "끄자", "끈다")
_STATUS_KEYS = ("상태", "어때")
_LIST_KEYS = ("기기목록", "어떤기기", "장치목록", "기기뭐가", "디바이스목록")


_POLITE_TAIL_RE = re.compile(
    r"\s*(알려\s*줘|알려\s*주세요|알려\s*달라|"
    r"보여\s*줘|보여\s*주세요|"
    r"해\s*줘|해\s*주세요|"
    r"주세요|줄래|줄래요|주실래요|"
    r"어때|어떤지|"
    r"줘|요|해)?\s*[.?!~…]*\s*$"
)


def _strip_polite(text: str) -> str:
    """한국어 정중/요청 어미 제거 — device 토큰 추출용."""
    out = text.strip()
    # 한 번에 안 떼지는 케이스 (예: "X 알려 줘") 대비 최대 두 번 시도
    for _ in range(2):
        m = _POLITE_TAIL_RE.search(out)
        if m and m.group(0).strip():
            out = out[: m.start()].strip()
        else:
            break
    return out


_COMPOUND_RE = re.compile(
    r"(하고|그리고|및\s|와\s|랑\s|또한|또는|"
    r"끄고|켜고|꺼서|켜서|동시에)"
)


def _looks_compound(device_candidate: str) -> bool:
    """추출된 device 후보에 또 다른 액션 키워드가 끼어있으면 복합 명령 신호."""
    norm = _normalize(device_candidate)
    for k in (*_TURN_ON_KEYS, *_TURN_OFF_KEYS):
        if k in norm:
            return True
    if _COMPOUND_RE.search(device_candidate):
        return True
    return False


def _extract_device_for_action(text: str, action_word: str) -> str:
    """action 키워드를 텍스트에서 잘라내고 남는 토큰을 device 후보로 반환."""
    cleaned = text
    for k in (action_word, *( _TURN_ON_KEYS if action_word == "ON" else _TURN_OFF_KEYS if action_word == "OFF" else (action_word,))):
        cleaned = re.sub(re.escape(k), " ", cleaned)
    cleaned = _strip_polite(cleaned)
    cleaned = re.sub(r"[,!?.~…]+", " ", cleaned).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _route_home_iot(text: str, low: str) -> RoutedIntent | None:
    """Home_IOT 룰베이스 매칭. None 이면 미매칭."""
    # 1) 기기 목록 (디바이스 토큰 불필요)
    if any(k in low for k in _LIST_KEYS):
        return RoutedIntent(
            intent="home_iot.list_devices", domain="home_iot",
            operation="list_devices", confidence=0.9,
        )

    # 2) 상태 — "X 상태" / "X 어때"
    if any(k in low for k in _STATUS_KEYS):
        keyword = "상태" if "상태" in low else "어때"
        device = _extract_device_for_action(text, keyword)
        if device and not _looks_compound(device):
            return RoutedIntent(
                intent="home_iot.get_status", domain="home_iot",
                operation="get_status", device_id=device,
                confidence=0.75,
            )

    # 3) 끄기 — turn_off (먼저 검사: "꺼"가 "켜"보다 우선해야 "꺼줘" 가 켜로 안 잡힘)
    for k in _TURN_OFF_KEYS:
        if k in low:
            device = _extract_device_for_action(text, k)
            if device and not _looks_compound(device):
                return RoutedIntent(
                    intent="home_iot.turn_off", domain="home_iot",
                    operation="execute_action",
                    device_id=device, action="turn_off",
                    confidence=0.85, entities={"action": "turn_off"},
                )

    # 4) 켜기 — turn_on
    for k in _TURN_ON_KEYS:
        if k in low:
            device = _extract_device_for_action(text, k)
            if device and not _looks_compound(device):
                return RoutedIntent(
                    intent="home_iot.turn_on", domain="home_iot",
                    operation="execute_action",
                    device_id=device, action="turn_on",
                    confidence=0.85, entities={"action": "turn_on"},
                )
    return None


# ---------------- Top-level ----------------

def parse(text: str) -> RoutedIntent:
    low = _normalize(text)
    if not low:
        return RoutedIntent("unknown", "none", None, confidence=0.0)

    # Personal_Service: 날씨 우선 (가장 흔함)
    if _is_weather(low):
        when = _weather_when(low)
        return RoutedIntent(
            intent=f"weather.{when}", domain="personal_service",
            operation="get_weather", params={"when": when},
            confidence=0.85, entities={"when": when},
        )

    # Personal_Service: 시간
    if _is_time(low):
        return RoutedIntent(
            intent="time.now", domain="personal_service",
            operation="get_time", params={"field": "time"},
            confidence=0.9,
        )

    # Home_IOT 룰베이스
    hi = _route_home_iot(text, low)
    if hi is not None:
        return hi

    # Personal_Service: 리마인더 placeholder
    if _is_reminder(low):
        return RoutedIntent(
            intent="reminder.placeholder", domain="personal_service",
            operation="set_reminder", confidence=0.5,
        )

    return RoutedIntent("unknown", "none", None, confidence=0.0)
