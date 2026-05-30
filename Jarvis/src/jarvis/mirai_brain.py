"""Mirai_brain 핸드오버 클라이언트 (스켈레톤).

로컬 규칙으로 풀 수 없는 모호/복합 의도를 Mirai_brain(Gemini 기반 중앙 오케스트레이터)
으로 넘긴다. Mirai_brain은 아직 미가동이므로 현재는 **스텁**으로 동작하며,
`.env`의 `MIRAI_BRAIN_URL`이 설정되면 실제 REST 호출 경로를 사용한다.

표준 응답(dict) 형태 — OPERATING.md의 message/data 분리 원칙을 따른다:
    {
      "intent": str, "route": str, "entities": dict,
      "confidence": float, "resolved_by": str, "message": str
    }
"""
from __future__ import annotations

import os

try:
    from jarvis.gcloud import load_env  # 공용 .env 로더 재사용
except Exception:  # pragma: no cover
    def load_env() -> None:  # type: ignore
        pass


def _stub(intent: str, message: str, resolved_by: str) -> dict:
    return {
        "intent": intent,
        "route": "mirai_brain",
        "entities": {},
        "confidence": 0.0,
        "resolved_by": resolved_by,
        "message": message,
    }


def resolve(text: str, context: dict | None = None) -> dict:
    """텍스트를 Mirai_brain에 넘겨 구조화된 의도를 받는다. (현재 스텁)"""
    load_env()
    url = os.environ.get("MIRAI_BRAIN_URL")
    if not url:
        # Mirai_brain 미가동 — 핸드오버 보류
        return _stub(
            "handover.pending",
            "아직 그 요청은 제가 처리하지 못해요. 곧 배워둘게요.",
            "mirai_brain_stub",
        )
    try:
        import requests

        resp = requests.post(
            f"{url.rstrip('/')}/intent",
            json={"text": text, "context": context or {}},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        data.setdefault("route", "mirai_brain")
        data.setdefault("resolved_by", "mirai_brain")
        return data
    except Exception as e:
        return _stub(
            "handover.error",
            "죄송해요, 지금은 그 요청을 처리할 수 없어요.",
            f"mirai_brain_error:{type(e).__name__}",
        )
