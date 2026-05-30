"""Mirai_brain FastAPI 엔트리포인트.

Jarvis 가 호출하는 단일 진입점 `POST /intent`.
요청: `{text, context}` — Jarvis 측 `mirai_brain.resolve()` 기대 형식.
응답: `{intent, route, entities, confidence, resolved_by, message, data}` — Jarvis `Intent` 으로 매핑됨.

라우팅 순서:
1. 룰베이스 라우터 — 결정적·고속.
2. 룰베이스가 domain="none" 이면 Gemini 2.5 Flash fallback.
3. Gemini 결과:
   - personal_service / home_iot → 화이트리스트 검증 후 도메인 호출.
   - none → Gemini message 그대로 (chitchat).
4. Gemini 미설정/실패 → 기본 안내 멘트.
"""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

from .domains import home_iot as hi
from .domains import personal_service as ps
from .gemini import GeminiClient, GeminiError, GeminiResult, GeminiUnavailable
from .router import RoutedIntent, parse as route_parse

SERVICE_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(SERVICE_ROOT / ".env")

log = logging.getLogger("mirai_brain")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

PERSONAL_SERVICE_URL = os.getenv("PERSONAL_SERVICE_URL", "http://127.0.0.1:8100")
HOME_IOT_URL = os.getenv("HOME_IOT_URL", "http://127.0.0.1:8300")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


class IntentRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    text: str
    context: dict[str, Any] = Field(default_factory=dict)


class IntentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intent: str
    route: str
    entities: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    resolved_by: str = "mirai_brain"
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.gemini = GeminiClient(api_key=GEMINI_API_KEY, model=GEMINI_MODEL)
    log.info(
        "lifespan up: PS=%s HIOT=%s gemini=%s model=%s",
        PERSONAL_SERVICE_URL, HOME_IOT_URL,
        "enabled" if app.state.gemini.enabled else "disabled", GEMINI_MODEL,
    )
    yield
    log.info("lifespan down")


app = FastAPI(title="Mirai_brain", version="0.3.0", lifespan=lifespan)


@app.get("/healthz")
def healthz() -> dict:
    return {
        "ok": True, "service": "mirai_brain", "version": app.version,
        "gemini": app.state.gemini.enabled if hasattr(app.state, "gemini") else False,
    }


def _trace_id_from(context: dict) -> str:
    tid = context.get("trace_id") if isinstance(context, dict) else None
    return tid or f"jv-trace-{uuid.uuid4().hex[:12]}"


def _ok(*, intent, route, entities, confidence, resolved_by, message, data=None) -> IntentResponse:
    return IntentResponse(
        intent=intent, route=route, entities=entities, confidence=confidence,
        resolved_by=resolved_by, message=message, data=data or {},
    )


async def _dispatch_personal_service(
    *, operation: str, params: dict[str, Any], req_context: dict, trace_id: str,
) -> tuple[bool, str, dict[str, Any], str]:
    request_id, plan_id = ps.new_ids()
    body = await ps.call_command(
        base_url=PERSONAL_SERVICE_URL, operation=operation, params=params,
        request_id=request_id, plan_id=plan_id, trace_id=trace_id,
        context={"input_mode": req_context.get("input_mode", "voice"),
                 "locale": req_context.get("locale", "ko-KR")},
    )
    return bool(body.get("ok")), body["message"], body.get("data", {}), request_id


async def _dispatch_home_iot(
    *, operation: str, device_id: str | None, action: str | None,
    req_context: dict, trace_id: str,
) -> tuple[bool, str, dict[str, Any], str]:
    request_id, plan_id = hi.new_ids()
    body = await hi.call_command(
        base_url=HOME_IOT_URL, operation=operation,
        device_id=device_id, action=action,
        request_id=request_id, plan_id=plan_id, trace_id=trace_id,
        context={"input_mode": req_context.get("input_mode", "voice"),
                 "locale": req_context.get("locale", "ko-KR")},
    )
    return bool(body.get("ok")), body["message"], body.get("data", {}), request_id


@app.post("/intent", response_model=IntentResponse)
async def intent(req: IntentRequest) -> IntentResponse:
    text = req.text.strip()
    log.info("intent text=%r ctx_keys=%s", text, list(req.context.keys()))
    trace_id = _trace_id_from(req.context)

    # 1) 룰베이스
    routed: RoutedIntent = route_parse(text)
    log.info("rule → intent=%s domain=%s op=%s device=%r action=%r conf=%.2f",
             routed.intent, routed.domain, routed.operation,
             routed.device_id, routed.action, routed.confidence)

    if routed.domain == "personal_service" and routed.operation:
        try:
            ok, msg, ps_data, rid = await _dispatch_personal_service(
                operation=routed.operation, params=routed.params,
                req_context=req.context, trace_id=trace_id,
            )
            return _ok(
                intent=routed.intent, route="personal_service",
                entities=routed.entities, confidence=routed.confidence,
                resolved_by="mirai_brain.router+personal_service",
                message=msg,
                data={"ok": ok, "trace_id": trace_id, "request_id": rid, "ps_data": ps_data},
            )
        except ps.DomainCallError as exc:
            log.error("PS 호출 실패 (rule): %s", exc)
            return _ok(
                intent=routed.intent, route="personal_service",
                entities=routed.entities, confidence=routed.confidence,
                resolved_by="mirai_brain.router",
                message="죄송해요, 지금은 그 정보를 가져올 수 없어요.",
                data={"error": str(exc), "trace_id": trace_id},
            )

    if routed.domain == "home_iot" and routed.operation:
        try:
            ok, msg, hi_data, rid = await _dispatch_home_iot(
                operation=routed.operation, device_id=routed.device_id,
                action=routed.action, req_context=req.context, trace_id=trace_id,
            )
            return _ok(
                intent=routed.intent, route="home_iot",
                entities=routed.entities, confidence=routed.confidence,
                resolved_by="mirai_brain.router+home_iot",
                message=msg,
                data={"ok": ok, "trace_id": trace_id, "request_id": rid, "hi_data": hi_data},
            )
        except hi.DomainCallError as exc:
            log.error("HIOT 호출 실패 (rule): %s", exc)
            return _ok(
                intent=routed.intent, route="home_iot",
                entities=routed.entities, confidence=routed.confidence,
                resolved_by="mirai_brain.router",
                message="죄송해요, 지금은 기기를 제어할 수 없어요.",
                data={"error": str(exc), "trace_id": trace_id},
            )

    if routed.domain not in ("none", "personal_service", "home_iot"):
        return _ok(
            intent=routed.intent, route="mirai_brain",
            entities=routed.entities, confidence=routed.confidence,
            resolved_by="mirai_brain.router",
            message="해당 도메인 연결은 아직 준비 중이에요.",
            data={"routed_domain": routed.domain, "error": "domain_not_wired"},
        )

    # 2) Gemini fallback
    gemini: GeminiClient = app.state.gemini
    if not gemini.enabled:
        return _ok(
            intent="unknown", route="mirai_brain",
            entities=routed.entities, confidence=0.0,
            resolved_by="mirai_brain.router",
            message="아직 그 요청은 제가 잘 이해하지 못했어요. 다시 말씀해 주세요.",
            data={"trace_id": trace_id, "gemini": "disabled"},
        )

    try:
        gres: GeminiResult = await gemini.classify(text)
    except (GeminiUnavailable, GeminiError) as exc:
        log.error("Gemini 실패: %s", exc)
        return _ok(
            intent="unknown", route="mirai_brain",
            entities=routed.entities, confidence=0.0,
            resolved_by="mirai_brain.router",
            message="아직 그 요청은 제가 잘 이해하지 못했어요. 다시 말씀해 주세요.",
            data={"trace_id": trace_id, "gemini": "error", "error": str(exc)},
        )

    log.info("gemini → intent=%s domain=%s op=%s params=%s conf=%.2f",
             gres.intent, gres.domain, gres.operation, gres.params, gres.confidence)

    # 2a) Personal_Service 라우팅
    if gres.domain == "personal_service" and gres.operation:
        try:
            ok, msg, ps_data, rid = await _dispatch_personal_service(
                operation=gres.operation, params=gres.params,
                req_context=req.context, trace_id=trace_id,
            )
            return _ok(
                intent=gres.intent, route="personal_service",
                entities=gres.params, confidence=gres.confidence,
                resolved_by="mirai_brain.gemini+personal_service",
                message=msg,
                data={"ok": ok, "trace_id": trace_id, "request_id": rid,
                      "ps_data": ps_data,
                      "gemini": {"reasoning": gres.reasoning, "intent": gres.intent}},
            )
        except ps.DomainCallError as exc:
            log.error("PS 호출 실패 (gemini): %s", exc)
            return _ok(
                intent=gres.intent, route="personal_service",
                entities=gres.params, confidence=gres.confidence,
                resolved_by="mirai_brain.gemini",
                message="죄송해요, 지금은 그 정보를 가져올 수 없어요.",
                data={"error": str(exc), "trace_id": trace_id},
            )

    # 2b) Home_IOT 라우팅 — params에서 device_id/action 추출
    if gres.domain == "home_iot" and gres.operation:
        device_id = gres.params.get("device_id")
        action = gres.params.get("action")
        try:
            ok, msg, hi_data, rid = await _dispatch_home_iot(
                operation=gres.operation, device_id=device_id, action=action,
                req_context=req.context, trace_id=trace_id,
            )
            return _ok(
                intent=gres.intent, route="home_iot",
                entities={"device_id": device_id, "action": action},
                confidence=gres.confidence,
                resolved_by="mirai_brain.gemini+home_iot",
                message=msg,
                data={"ok": ok, "trace_id": trace_id, "request_id": rid,
                      "hi_data": hi_data,
                      "gemini": {"reasoning": gres.reasoning, "intent": gres.intent}},
            )
        except hi.DomainCallError as exc:
            log.error("HIOT 호출 실패 (gemini): %s", exc)
            return _ok(
                intent=gres.intent, route="home_iot",
                entities=gres.params, confidence=gres.confidence,
                resolved_by="mirai_brain.gemini",
                message="죄송해요, 지금은 기기를 제어할 수 없어요.",
                data={"error": str(exc), "trace_id": trace_id},
            )

    # 2c) chitchat / clarify
    return _ok(
        intent=gres.intent or "chitchat.reply", route="mirai_brain",
        entities=gres.params, confidence=gres.confidence,
        resolved_by="mirai_brain.gemini",
        message=gres.message or "네, 알겠습니다.",
        data={"trace_id": trace_id, "gemini": {"reasoning": gres.reasoning, "intent": gres.intent}},
    )
