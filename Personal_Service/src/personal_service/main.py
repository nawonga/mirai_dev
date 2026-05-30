"""Personal_Service FastAPI 엔트리포인트.

OPERATING.md §3.3 표준 JSON 계약을 단일 진입점 `POST /command` 로 노출한다.
부팅 시 weather 캐시 로드 + 백그라운드 갱신 스케줄러 시작 (KMA 키 있을 때만).
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from .contracts import CommandRequest, CommandResponse
from .operations import get_time, get_weather
from .weather.cache import WeatherCache, resolve_cache_path
from .weather.scheduler import WeatherScheduler

SERVICE_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(SERVICE_ROOT / ".env")

log = logging.getLogger("personal_service")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

TZ = ZoneInfo(os.getenv("PS_TIMEZONE", "Asia/Seoul"))
KMA_SERVICE_KEY = os.getenv("KMA_SERVICE_KEY", "").strip()
WEATHER_NX = int(os.getenv("WEATHER_LOCATION_NX", "62"))
WEATHER_NY = int(os.getenv("WEATHER_LOCATION_NY", "126"))
WEATHER_LOCATION_NAME = os.getenv("WEATHER_LOCATION_NAME", "")
WEATHER_CACHE_PATH = resolve_cache_path(
    os.getenv("WEATHER_CACHE_PATH", "storage/weather_cache.json"),
    SERVICE_ROOT,
)

# 구현 완료된 operation
IMPLEMENTED_OPERATIONS = {"get_time", "get_weather"}
# OPERATING.md §3.4에 정의되어 있으나 아직 미구현
PLANNED_OPERATIONS = {"set_reminder", "list_reminders", "cancel_reminder", "update_reminder"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache = WeatherCache(WEATHER_CACHE_PATH, WEATHER_LOCATION_NAME)
    cache.load_from_disk()
    scheduler = WeatherScheduler(
        cache=cache,
        service_key=KMA_SERVICE_KEY,
        nx=WEATHER_NX,
        ny=WEATHER_NY,
        tz=TZ,
    )
    scheduler.start()
    app.state.weather_cache = cache
    app.state.weather_scheduler = scheduler
    app.state.kma_key_set = bool(KMA_SERVICE_KEY)
    log.info(
        "lifespan up: kma_key=%s nx=%d ny=%d location=%r cache=%s",
        "set" if KMA_SERVICE_KEY else "missing",
        WEATHER_NX, WEATHER_NY, WEATHER_LOCATION_NAME, WEATHER_CACHE_PATH,
    )
    try:
        yield
    finally:
        await scheduler.stop()
        log.info("lifespan down")


app = FastAPI(title="Personal_Service", version="0.2.0", lifespan=lifespan)


def _carry_trace(req: CommandRequest, extra: dict) -> dict:
    out = {"operation": req.operation, "request_id": req.request_id}
    if req.plan_id is not None:
        out["plan_id"] = req.plan_id
    if req.trace_id is not None:
        out["trace_id"] = req.trace_id
    out.update(extra)
    return out


def _err(req: CommandRequest, message: str, **err_data) -> CommandResponse:
    return CommandResponse(ok=False, message=message, data=_carry_trace(req, err_data))


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "service": "personal_service", "version": app.version}


@app.post("/command", response_model=CommandResponse)
def command(req: CommandRequest) -> CommandResponse:
    log.info(
        "command op=%s request_id=%s trace_id=%s",
        req.operation, req.request_id, req.trace_id,
    )

    op = req.operation

    if op == "get_time":
        try:
            message, extra = get_time.execute(req.params, TZ)
        except ValueError as exc:
            return _err(req, "요청 형식이 올바르지 않아요.", error=str(exc))
        return CommandResponse(ok=True, message=message, data=_carry_trace(req, extra))

    if op == "get_weather":
        try:
            ok, message, extra = get_weather.execute(
                req.params, TZ,
                cache=app.state.weather_cache,
                service_key_set=app.state.kma_key_set,
            )
        except ValueError as exc:
            return _err(req, "요청 형식이 올바르지 않아요.", error=str(exc))
        return CommandResponse(ok=ok, message=message, data=_carry_trace(req, extra))

    if op in PLANNED_OPERATIONS:
        return _err(req, "해당 기능은 아직 준비 중이에요.", error="planned but not yet implemented")

    return _err(req, "요청하신 동작을 이해하지 못했어요.", error="unknown operation")


@app.post("/admin/refresh-weather")
async def refresh_weather() -> dict:
    """수동 즉시 fetch (디버깅/운영용). 키 미설정 시 503."""
    scheduler: WeatherScheduler = app.state.weather_scheduler
    if not scheduler.enabled:
        raise HTTPException(status_code=503, detail="KMA_SERVICE_KEY 미설정")
    ok = await scheduler.fetch_once()
    entry = app.state.weather_cache.get()
    return {
        "ok": ok,
        "cache_present": entry is not None,
        "base_date": entry.base_date if entry else None,
        "base_time": entry.base_time if entry else None,
        "fetched_at": entry.fetched_at.isoformat(timespec="seconds") if entry else None,
    }
