"""Personal_Service 도메인 클라이언트.

OPERATING.md §통신 — 표준 JSON envelope (`POST /command`).
모든 호출에 request_id/plan_id/trace_id 를 전파한다.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx

log = logging.getLogger("mirai_brain.domains.personal_service")

DEFAULT_TIMEOUT = 5.0  # 도메인 호출 타임아웃 (Jarvis 응답성 우선)


class DomainCallError(RuntimeError):
    """도메인 호출 실패 (네트워크/타임아웃/형식)."""


async def call_command(
    *,
    base_url: str,
    operation: str,
    params: dict[str, Any],
    request_id: str,
    plan_id: str,
    trace_id: str,
    requester: str | None = None,
    context: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Personal_Service `POST /command` 호출 → 응답 dict 그대로 반환.

    응답 envelope: `{ok, message, data}`. 호출 실패는 `DomainCallError`.
    """
    envelope = {
        "domain": "personal_service",
        "operation": operation,
        "params": params,
        "request_id": request_id,
        "plan_id": plan_id,
        "trace_id": trace_id,
        "source": "mirai_brain",
        "context": context or {},
    }
    if requester:
        envelope["requester"] = requester

    log.info("→ PS op=%s request_id=%s trace_id=%s", operation, request_id, trace_id)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{base_url.rstrip('/')}/command", json=envelope)
    except httpx.HTTPError as exc:
        raise DomainCallError(f"HTTP 실패: {exc}") from exc

    if resp.status_code != 200:
        raise DomainCallError(f"HTTP {resp.status_code}: {resp.text[:200]}")

    try:
        body = resp.json()
    except ValueError as exc:
        raise DomainCallError(f"JSON 파싱 실패: {exc}") from exc

    if not isinstance(body, dict) or "ok" not in body or "message" not in body:
        raise DomainCallError(f"envelope 형식 오류: {body!r}")

    log.info("← PS op=%s ok=%s", operation, body.get("ok"))
    return body


def new_ids() -> tuple[str, str]:
    """Mirai_brain 진입 시 신규 발급할 request_id, plan_id."""
    return f"mb-req-{uuid.uuid4().hex[:12]}", f"mb-plan-{uuid.uuid4().hex[:12]}"
