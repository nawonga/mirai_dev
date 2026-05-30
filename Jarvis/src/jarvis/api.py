"""Jarvis 텍스트 인입 API — POST /api/v1/command.

text_command_api.md (Jarvis docs) 계약 구현. 외부 (iOS 단축어, 웹훅, 스크립트)
가 STT 결과와 동일한 텍스트를 보내면 intent.parse() 부터 시작 — 음성 경로와
완전히 동일한 Local-First → Mirai_brain 핸드오버.

실행 (수동):
    PYTHONPATH=src venv/bin/uvicorn jarvis.api:app --host 0.0.0.0 --port 8400

운영: systemd user service `jarvis-api.service`.
"""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from jarvis import intent as intent_mod

SERVICE_ROOT = Path(__file__).resolve().parents[2]  # Jarvis 루트
load_dotenv(SERVICE_ROOT / ".env")

log = logging.getLogger("jarvis.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

JARVIS_API_TOKEN = os.getenv("JARVIS_API_TOKEN", "").strip()

# intent.name 이 이 집합에 들면 실패로 간주 (ok=False, executed=False)
FAILED_INTENTS = frozenset({"unknown", "handover.pending", "handover.error"})


class CommandRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    text: str = Field(..., min_length=1, description="STT 출력 대체 명령 문자열")
    source: str = "external"
    user: str | None = None
    request_id: str | None = None
    locale: str = "ko-KR"
    speak: bool = False     # 추후 — 현재는 무시. Jarvis 데몬과의 TTS 호출 충돌 회피.
    dry_run: bool = False


class CommandResponseData(BaseModel):
    intent: str
    entities: dict[str, Any] = Field(default_factory=dict)
    route: str
    resolved_by: str
    confidence: float = 0.0
    executed: bool = True
    request_id: str
    trace_id: str
    speak_skipped: bool = False


class CommandResponse(BaseModel):
    ok: bool
    message: str
    data: CommandResponseData


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not JARVIS_API_TOKEN:
        log.warning("JARVIS_API_TOKEN 미설정 — 모든 호출 503 거부")
    else:
        log.info("lifespan up: token=set (len=%d) MB=%s",
                 len(JARVIS_API_TOKEN), os.getenv("MIRAI_BRAIN_URL", "(미설정)"))
    yield
    log.info("lifespan down")


app = FastAPI(title="Jarvis Text Command API", version="0.1.0", lifespan=lifespan)
bearer = HTTPBearer(auto_error=False)


def verify_token(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
    """Bearer token 검증. 토큰 미설정 시 503. 잘못된 토큰 401."""
    if not JARVIS_API_TOKEN:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="API token not configured")
    if creds is None or creds.scheme.lower() != "bearer" or creds.credentials != JARVIS_API_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or missing Bearer token")


@app.get("/healthz")
def healthz() -> dict:
    return {
        "ok": True, "service": "jarvis-api", "version": app.version,
        "token_configured": bool(JARVIS_API_TOKEN),
    }


@app.post("/api/v1/command", response_model=CommandResponse)
async def command(req: CommandRequest, _: None = Depends(verify_token)) -> CommandResponse:
    rid = req.request_id or f"ext-{uuid.uuid4().hex[:12]}"
    tid = f"trace-{uuid.uuid4().hex[:12]}"
    log.info("command source=%s user=%s text=%r rid=%s tid=%s dry_run=%s",
             req.source, req.user, req.text, rid, tid, req.dry_run)

    if req.dry_run:
        local = intent_mod.parse_local(req.text)
        if local is not None:
            return CommandResponse(
                ok=True,
                message=local.reply or "(no reply)",
                data=CommandResponseData(
                    intent=local.name, entities=local.entities,
                    route=local.route, resolved_by=local.resolved_by,
                    confidence=local.confidence, executed=False,
                    request_id=rid, trace_id=tid, speak_skipped=req.speak,
                ),
            )
        return CommandResponse(
            ok=True,
            message="(dry_run) 로컬 규칙 미해결 — Mirai_brain 호출 생략",
            data=CommandResponseData(
                intent="dry_run.unresolved", route="dry_run",
                resolved_by="local.dry_run", executed=False,
                request_id=rid, trace_id=tid, speak_skipped=req.speak,
            ),
        )

    # 정식 흐름 — 음성 경로와 동일 (Local-First → Mirai_brain handover)
    intent = intent_mod.parse(req.text)
    msg = intent.reply or "무슨 말씀인지 잘 모르겠어요."
    ok = intent.name not in FAILED_INTENTS
    log.info("response intent=%s route=%s by=%s ok=%s rid=%s",
             intent.name, intent.route, intent.resolved_by, ok, rid)
    return CommandResponse(
        ok=ok, message=msg,
        data=CommandResponseData(
            intent=intent.name, entities=intent.entities,
            route=intent.route, resolved_by=intent.resolved_by,
            confidence=intent.confidence, executed=ok,
            request_id=rid, trace_id=tid, speak_skipped=req.speak,
        ),
    )
