"""Home_IOT 도메인 클라이언트 — `POST /command` (engine.handle_json 의 HTTP 진입점).

응답 envelope 은 Personal_Service 와 동일하게 `{ok, message, data}`.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx

log = logging.getLogger("mirai_brain.domains.home_iot")

DEFAULT_TIMEOUT = 5.0


class DomainCallError(RuntimeError):
    pass


async def call_command(
    *,
    base_url: str,
    operation: str,
    device_id: str | None,
    action: str | None,
    request_id: str,
    plan_id: str,
    trace_id: str,
    context: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "domain": "home_iot",
        "operation": operation,
        "request_id": request_id,
        "plan_id": plan_id,
        "trace_id": trace_id,
        "source": "mirai_brain",
        "context": context or {},
    }
    if device_id is not None:
        envelope["device_id"] = device_id
    if action is not None:
        envelope["action"] = action

    log.info("→ HIOT op=%s device=%r action=%r request_id=%s trace_id=%s",
             operation, device_id, action, request_id, trace_id)
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
    log.info("← HIOT op=%s ok=%s", operation, body.get("ok"))
    return body


def new_ids() -> tuple[str, str]:
    return f"mb-req-{uuid.uuid4().hex[:12]}", f"mb-plan-{uuid.uuid4().hex[:12]}"
