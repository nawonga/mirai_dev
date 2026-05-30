"""Gemini 2.5 Flash fallback — 룰베이스 미해결 의도 분류 + chitchat 응답.

OPERATING.md §"Centralized Intelligence" 의 '2차 인텐트 분석' 책임.
저신뢰/모호 발화를 받아 (a) 알려진 operation 으로 라우팅 또는 (b) 짧은 한국어
conversational message 를 생성한다.

graceful: GEMINI_API_KEY 미설정 시 `GeminiUnavailable` 예외 → 호출자가 기본
fallback 멘트로 응답.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger("mirai_brain.gemini")

# Personal_Service 가 실제 디스패치 가능한 operation. 그 외는 chitchat 으로 강제 다운그레이드.
ALLOWED_OPERATIONS: dict[str, set[str]] = {
    "personal_service": {
        "get_time", "get_weather",
        "set_reminder", "list_reminders", "cancel_reminder", "update_reminder",
    },
    "home_iot": {
        "list_devices", "list_actions", "execute_action", "get_status",
    },
    "aqua_dcs": set(),    # 도메인 클라이언트 미연결
}

# weather 의 `when` 은 PS 측 제약 (now/today/tomorrow) 에 맞춰 normalize
WEATHER_WHEN_ALIASES = {
    "now": "now", "현재": "now", "지금": "now",
    "today": "today", "오늘": "today",
    "tomorrow": "tomorrow", "내일": "tomorrow", "낼": "tomorrow",
}

SYSTEM_INSTRUCTION = """\
당신은 '미라이 스페이스'의 중앙 오케스트레이터입니다. 라즈베리파이 5에서 동작하는
한국어 사용자용 개인 스마트홈/생활 보조 AI 의 두뇌 역할을 합니다.

사용자의 한 줄 발화를 받아 두 가지 중 하나로 응답합니다:
1. 알려진 도메인 operation 으로 라우팅 (구조화 JSON)
2. 도메인 호출이 불가능한 일상 대화/요청이면 짧은 한국어 message 생성

알려진 도메인/operation:
- personal_service:
  - get_time(field: time|date|weekday|all, offset_days: int)  — 시각/날짜/요일/상대시간
  - get_weather(when: now|today|tomorrow)                   — 기상청 단기예보 캐시
  - set_reminder / list_reminders / cancel_reminder         — 알람·리마인더 (현재 미구현, planned)
- home_iot:
  - list_devices()                                          — 등록된 기기 목록
  - get_status(device_id)                                   — 한 기기 현재 상태
  - execute_action(device_id, action)                       — 기기 제어
    - **device_id 는 반드시 아래 alias 중 하나를 정확히 사용**:
        * TV          : "TV", "티비", "텔레비전", "거실 티비"
        * 거실 조명    : "거실등", "거실 조명", "거실 불"
        * 에어컨       : "에어컨", "ac"
      자연어 그대로 ("거실 TV", "방 조명" 등) 보내면 매칭 실패함.
    - action 표준 토큰:
        turn_on / turn_off : 켜기/끄기 (Home_IOT 가 power_on/power_off/power 토글 능력에 자동 매핑)
        power              : 명시 토글
        volume_up / volume_down / mute : TV
        temp_up / temp_down            : 에어컨
    - 복합 명령(두 가지 이상의 기기 제어)이면 **가장 중요한 한 동작만 실행**하고,
      message 에 "다른 것도 도와드릴게요. 다시 말씀해 주세요" 같은 안내 포함.
- aqua_dcs: (현재 라우팅 미연결 — domain="none" 으로 처리)

응답 규칙:
- 출력은 반드시 아래 JSON 스키마 한 객체. 다른 텍스트 금지.
- 발화가 명백히 알려진 operation 으로 매핑되면 domain/operation/params 채우고
  message 는 "준비할게요" 수준의 짧은 안내(실제 데이터는 도메인이 채움).
- 일상 대화/메뉴 추천/감정 공감/규칙 밖 질문은 domain="none", operation=null,
  message 에 1~2문장 친근한 한국어 답변.
- 알려지지 않은 operation 을 만들지 마세요.
- weather 의 when 은 정확히 "now" | "today" | "tomorrow" 중 하나.
- confidence 는 0.0~1.0.
- reasoning 은 디버그용 한 줄 한국어.

JSON 스키마:
{
  "intent": str,            // 예: "weather.tomorrow", "chitchat.suggestion", "clarify.weather"
  "domain": "personal_service" | "home_iot" | "aqua_dcs" | "none",
  "operation": str | null,
  "params": object,
  "message": str,
  "confidence": number,
  "reasoning": str
}
"""


class GeminiUnavailable(RuntimeError):
    """키 미설정 또는 SDK 미사용 가능."""


class GeminiError(RuntimeError):
    """API 호출 실패 또는 응답 파싱 실패."""


@dataclass
class GeminiResult:
    intent: str
    domain: str
    operation: str | None
    params: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


def _normalize_weather_params(params: dict[str, Any]) -> dict[str, Any]:
    """weather operation 의 when 을 PS 가 받는 값으로 정규화."""
    when = str(params.get("when", "now")).strip().lower()
    when = WEATHER_WHEN_ALIASES.get(when, when)
    if when not in ("now", "today", "tomorrow"):
        when = "now"
    return {"when": when}


def _enforce_whitelist(result: GeminiResult) -> GeminiResult:
    """Gemini 가 알려지지 않은 operation 을 만들면 chitchat 으로 강등."""
    if result.domain == "none" or result.operation is None:
        result.operation = None
        result.params = {}
        return result
    allowed = ALLOWED_OPERATIONS.get(result.domain, set())
    if result.operation not in allowed:
        log.warning("Gemini 가 미허용 operation 제안: domain=%s op=%s → chitchat 으로 강등",
                    result.domain, result.operation)
        result.domain = "none"
        result.operation = None
        result.params = {}
        if not result.message:
            result.message = "해당 기능은 아직 제공되지 않아요."
        return result
    # operation 별 params 정규화
    if result.domain == "personal_service" and result.operation == "get_weather":
        result.params = _normalize_weather_params(result.params)
    return result


def _parse_payload(text: str) -> GeminiResult:
    """Gemini 응답 JSON 문자열 → GeminiResult."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GeminiError(f"JSON 파싱 실패: {exc}; payload={text[:200]!r}") from exc
    if not isinstance(data, dict):
        raise GeminiError(f"객체 아님: {data!r}")
    result = GeminiResult(
        intent=str(data.get("intent", "gemini.unknown")),
        domain=str(data.get("domain", "none")),
        operation=(data.get("operation") if data.get("operation") not in ("", "null") else None),
        params=dict(data.get("params") or {}),
        message=str(data.get("message", "")).strip(),
        confidence=float(data.get("confidence", 0.0) or 0.0),
        reasoning=str(data.get("reasoning", "")),
        raw=data,
    )
    return _enforce_whitelist(result)


class GeminiClient:
    """비동기 Gemini 호출 래퍼."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", timeout: float = 8.0) -> None:
        self.api_key = (api_key or "").strip()
        self.model = model
        self.timeout = timeout
        if not self.api_key:
            self._client = None
            return
        try:
            from google import genai  # type: ignore
            self._genai = genai
            self._client = genai.Client(api_key=self.api_key)
        except Exception as exc:  # pragma: no cover
            log.warning("google-genai 초기화 실패: %s", exc)
            self._client = None

    @property
    def enabled(self) -> bool:
        return self._client is not None

    async def classify(self, text: str) -> GeminiResult:
        if not self._client:
            raise GeminiUnavailable("GEMINI_API_KEY 미설정 또는 SDK 초기화 실패")
        from google.genai import types  # type: ignore
        try:
            response = await self._client.aio.models.generate_content(
                model=self.model,
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    temperature=0.3,
                    max_output_tokens=512,
                    # 2.5 Flash 는 thinking 기본 ON. fallback 분류는 빠른 응답이 중요해 비활성.
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
        except Exception as exc:
            raise GeminiError(f"호출 실패: {type(exc).__name__}: {exc}") from exc
        text_out = (response.text or "").strip()
        log.info("Gemini raw len=%d", len(text_out))
        return _parse_payload(text_out)
