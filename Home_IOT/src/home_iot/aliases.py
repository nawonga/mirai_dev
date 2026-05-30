"""Alias 정규화 — 음성 표현/별칭 → canonical device id / action id.

(docs/ALIAS_ACTION_STANDARD.md) 실행은 항상 canonical id 기준. alias는 해석 보조 수단일 뿐.
device alias는 레지스트리의 각 device "aliases"에서, action alias는 아래 정적 맵에서 해석한다.
"""
from __future__ import annotations

import re

# 정규화된 음성 토큰 → 추상 액션. (canonical action id가 직접 와도 통과)
_ACTION_ALIASES: dict[str, str] = {
    "켜": "turn_on", "켜줘": "turn_on", "온": "turn_on", "on": "turn_on",
    "꺼": "turn_off", "꺼줘": "turn_off", "오프": "turn_off", "off": "turn_off",
    "전원": "power", "파워": "power",
    "볼륨올려": "volume_up", "소리키워": "volume_up", "음량올려": "volume_up", "볼륨업": "volume_up",
    "볼륨내려": "volume_down", "소리줄여": "volume_down", "음량내려": "volume_down", "볼륨다운": "volume_down",
    "음소거": "mute", "뮤트": "mute",
    "온도올려": "temp_up", "더따뜻하게": "temp_up",
    "온도내려": "temp_down", "더시원하게": "temp_down",
}


def normalize(text: str) -> str:
    """공백/문장부호 제거, 소문자화(한글·영숫자만)."""
    return re.sub(r"[^\w가-힣]", "", (text or "")).lower()


def resolve_device(token: str, reg: dict) -> str | None:
    """device id 또는 alias → canonical device id."""
    norm = normalize(token)
    if not norm:
        return None
    for did, cfg in reg.get("devices", {}).items():
        if normalize(did) == norm:
            return did
        for a in cfg.get("aliases", []):
            if normalize(a) == norm:
                return did
    return None


def resolve_action(token: str, supported: set[str]) -> str | None:
    """action 토큰 → 해당 기기가 지원하는 canonical action id.

    turn_on/turn_off 추상 액션은 기기 능력에 맞춰 power_on/off(상태형) 또는 power(토글)로 매핑.
    """
    norm = normalize(token)
    abstract = _ACTION_ALIASES.get(norm, norm)

    if abstract == "turn_on":
        for c in ("power_on", "power"):
            if c in supported:
                return c
        return None
    if abstract == "turn_off":
        for c in ("power_off", "power"):
            if c in supported:
                return c
        return None
    return abstract if abstract in supported else None
