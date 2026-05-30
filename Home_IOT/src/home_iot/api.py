"""Home_IOT FastAPI 래퍼 — 캐노니컬 `engine.handle_json()` 의 HTTP 진입점.

Mirai_brain 이 `POST /command` 로 호출하면 그대로 위임한다. 기존 CLI
(`main.py handle-json`) 과 동일 동작, 다만 인터페이스만 HTTP.

요청 envelope:
    {domain, operation, device_id?, action?, request_id, plan_id?, trace_id?,
     source?, context?}

응답: `{ok, message, data}` — `engine.handle_json` 결과 그대로.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

from . import engine, registry

SERVICE_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(SERVICE_ROOT / ".env")

log = logging.getLogger("home_iot")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


class CommandRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    operation: str
    request_id: str
    domain: str | None = None  # "home_iot" — 확인용, 없어도 동작
    device_id: str | None = None
    action: str | None = None
    plan_id: str | None = None
    trace_id: str | None = None
    source: str | None = "mirai_brain"
    context: dict[str, Any] = Field(default_factory=dict)


class CommandResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    ok: bool
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 부팅 시 registry 1회 로드 → in-memory 캐시
    app.state.registry = registry.load_registry()
    n = len(app.state.registry.get("devices", {}))
    log.info("lifespan up: registry devices=%d", n)
    yield
    log.info("lifespan down")


app = FastAPI(title="Home_IOT", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
def healthz() -> dict:
    n = len(app.state.registry.get("devices", {})) if hasattr(app.state, "registry") else 0
    return {"ok": True, "service": "home_iot", "version": app.version, "devices": n}


@app.post("/command", response_model=CommandResponse)
def command(req: CommandRequest) -> CommandResponse:
    log.info("command op=%s device=%r action=%r request_id=%s trace_id=%s",
             req.operation, req.device_id, req.action, req.request_id, req.trace_id)
    result = engine.handle_json(req.model_dump(exclude_none=False), reg=app.state.registry)
    return CommandResponse(**result)
