"""기상 캐시 갱신 백그라운드 태스크.

전략:
1. 부팅 시 디스크 캐시 로드.
2. 캐시 없거나 stale 이면 즉시 1회 fetch.
3. 다음 KMA 발표 + 마진 시각까지 sleep, 깨어나서 fetch, 반복.
4. fetch 실패 시 다음 발표시각까지 stale cache 유지 (서비스는 계속 응답).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from .cache import WeatherCache
from .kma_client import KmaError, fetch_now, next_fetch_time

log = logging.getLogger("personal_service.weather.scheduler")

# fetch 실패 후 재시도 간격 (다음 발표까지가 너무 멀 때 백오프)
RETRY_DELAY_SECONDS = 60 * 10  # 10분


class WeatherScheduler:
    def __init__(
        self,
        *,
        cache: WeatherCache,
        service_key: str,
        nx: int,
        ny: int,
        tz: ZoneInfo,
    ) -> None:
        self.cache = cache
        self.service_key = service_key
        self.nx = nx
        self.ny = ny
        self.tz = tz
        self._task: asyncio.Task | None = None
        self._stopped = asyncio.Event()

    @property
    def enabled(self) -> bool:
        return bool(self.service_key)

    async def fetch_once(self) -> bool:
        """수동/즉시 fetch — 성공 시 True. 실패 시 False (cache 유지)."""
        if not self.service_key:
            log.warning("KMA_SERVICE_KEY 미설정 — fetch 스킵")
            return False
        try:
            now = datetime.now(self.tz)
            parsed = await fetch_now(
                service_key=self.service_key, nx=self.nx, ny=self.ny, tz=self.tz, now=now,
            )
            await self.cache.save(parsed, fetched_at=now)
            return True
        except KmaError as exc:
            log.error("KMA fetch 실패: %s", exc)
            return False
        except Exception:
            log.exception("KMA fetch 예외")
            return False

    async def _loop(self) -> None:
        # 부팅 시 캐시 비어있거나 stale 이면 즉시 fetch.
        now = datetime.now(self.tz)
        entry = self.cache.get()
        if entry is None or entry.is_stale(now):
            log.info("부팅 fetch 실행 (캐시 없음 또는 stale)")
            await self.fetch_once()

        while not self._stopped.is_set():
            now = datetime.now(self.tz)
            try:
                target = next_fetch_time(now)
            except KmaError:
                target = now
            sleep_sec = max(1.0, (target - now).total_seconds())
            log.info("다음 갱신 예정: %s (%.0fs 후)", target.isoformat(timespec="minutes"), sleep_sec)
            try:
                await asyncio.wait_for(self._stopped.wait(), timeout=sleep_sec)
                # _stopped 가 set 되면 wait_for 가 정상 반환 → 루프 탈출
                return
            except asyncio.TimeoutError:
                pass  # 정시 도달 — fetch 진행

            ok = await self.fetch_once()
            if not ok:
                # 실패: 짧은 백오프 후 재시도 (다음 발표까지 너무 길면)
                log.info("실패 백오프 %ds", RETRY_DELAY_SECONDS)
                try:
                    await asyncio.wait_for(self._stopped.wait(), timeout=RETRY_DELAY_SECONDS)
                    return
                except asyncio.TimeoutError:
                    await self.fetch_once()

    def start(self) -> None:
        if self._task is not None:
            return
        if not self.enabled:
            log.warning("KMA_SERVICE_KEY 미설정 — 스케줄러 시작 안 함 (캐시만 사용)")
            return
        self._task = asyncio.create_task(self._loop(), name="weather-scheduler")

    async def stop(self) -> None:
        self._stopped.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
