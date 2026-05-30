"""기상청 단기예보(`getVilageFcst`) 호출/파싱.

KMA 발표 시각: 매일 02:10/05:10/08:10/11:10/14:10/17:10/20:10/23:10 (KST).
요청 시 사용하는 `base_time` 은 발표 시각의 분을 떼어낸 `0200/0500/.../2300`.

본 모듈은 stateless. 호출자(스케줄러)가 `base_date`/`base_time` 을 계산해
넘기거나, `latest_base()` 헬퍼를 써서 현재 시각 기준 직전 발표를 사용한다.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx

log = logging.getLogger("personal_service.weather.kma")

# 기상청 API 허브 (apihub.kma.go.kr) — 인증은 `authKey` 파라미터.
# 참고: 공공데이터포털(apis.data.go.kr/.../serviceKey)과는 다른 게이트웨이.
KMA_HOST = "https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstInfoService_2.0"
KMA_PATH = "/getVilageFcst"

# 발표 시각의 hour (KST). 발표는 매시 10분에 publish 되지만 우리는
# 마진을 두고 `+ MARGIN_MINUTES` 이후에 fetch 한다.
BASE_HOURS = (2, 5, 8, 11, 14, 17, 20, 23)
PUBLISH_MARGIN_MINUTES = 15

# numOfRows: 12 카테고리 × ~71 시간 슬롯 ≈ 852 (3일 예보). 1000이면 충분.
DEFAULT_PAGE_SIZE = 1000

# 우리가 보존할 카테고리. 나머지(UUU/VVV/VEC 등)는 사용처 없어서 드롭.
KEEP_CATEGORIES = frozenset({"TMP", "TMN", "TMX", "SKY", "PTY", "POP", "REH", "WSD", "PCP", "SNO"})


class KmaError(RuntimeError):
    """KMA API 호출/응답 파싱 실패."""


def latest_base(now: datetime) -> tuple[str, str]:
    """`now` 기준, 이미 발표가 완료된 가장 최근 base_date/base_time 반환.

    KMA 발표는 HH:10 이지만, 우리는 `PUBLISH_MARGIN_MINUTES` 마진을 둔 시점부터
    해당 시각을 사용할 수 있다고 본다.
    """
    cutoff = now - timedelta(minutes=PUBLISH_MARGIN_MINUTES)
    candidates = []
    for offset in (0, 1):  # 오늘과 어제까지 후보 (자정 직후 케이스)
        day = (cutoff - timedelta(days=offset)).date()
        for hour in BASE_HOURS:
            slot = datetime(day.year, day.month, day.day, hour, 0, tzinfo=cutoff.tzinfo)
            if slot <= cutoff:
                candidates.append(slot)
    if not candidates:
        raise KmaError("base_time 후보 산출 실패 (시간대 미설정?)")
    pick = max(candidates)
    return pick.strftime("%Y%m%d"), pick.strftime("%H%M")


def next_fetch_time(now: datetime) -> datetime:
    """다음 fetch 가 가능해지는 시각 (= 다음 BASE_HOUR + 마진)."""
    margin = timedelta(minutes=PUBLISH_MARGIN_MINUTES)
    for offset in (0, 1):
        day = (now + timedelta(days=offset)).date()
        for hour in BASE_HOURS:
            slot = datetime(day.year, day.month, day.day, hour, 0, tzinfo=now.tzinfo) + margin
            if slot > now:
                return slot
    raise KmaError("next_fetch_time 산출 실패")


async def fetch_village_forecast(
    *,
    service_key: str,
    nx: int,
    ny: int,
    base_date: str,
    base_time: str,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """KMA `getVilageFcst` 호출 → 시간별 버킷으로 정규화된 dict 반환.

    Returns:
        {
            "base_date": "20260529",
            "base_time": "1100",
            "nx": 62, "ny": 126,
            "hourly": {
                "20260529T1200": {"TMP": "18", "SKY": "1", "PTY": "0", ...},
                ...
            },
            "daily": {
                "20260529": {"TMN": "12", "TMX": "21"},
                ...
            }
        }
    """
    params = {
        "authKey": service_key,
        "pageNo": "1",
        "numOfRows": str(DEFAULT_PAGE_SIZE),
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": str(nx),
        "ny": str(ny),
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.get(KMA_HOST + KMA_PATH, params=params)
        except httpx.HTTPError as exc:
            raise KmaError(f"HTTP 실패: {exc}") from exc

    if resp.status_code != 200:
        raise KmaError(f"HTTP {resp.status_code}: {resp.text[:200]}")

    # KMA 가 에러 시 XML 을 돌려주는 케이스(키 미등록 등) 방지
    ctype = resp.headers.get("content-type", "")
    if "json" not in ctype.lower() and not resp.text.lstrip().startswith("{"):
        raise KmaError(f"JSON 아님 (content-type={ctype}, body 앞부분={resp.text[:200]!r})")

    try:
        payload = resp.json()
    except ValueError as exc:
        raise KmaError(f"JSON 파싱 실패: {exc}") from exc

    return _parse_response(payload, nx=nx, ny=ny)


def _parse_response(payload: dict[str, Any], *, nx: int, ny: int) -> dict[str, Any]:
    try:
        header = payload["response"]["header"]
        result_code = header.get("resultCode")
        result_msg = header.get("resultMsg")
    except (KeyError, TypeError) as exc:
        raise KmaError(f"응답 envelope 파싱 실패: {payload!r}") from exc

    if result_code != "00":
        raise KmaError(f"KMA error code={result_code} msg={result_msg}")

    body = payload["response"].get("body") or {}
    items_wrap = body.get("items") or {}
    items = items_wrap.get("item") or []
    if not items:
        raise KmaError("응답에 item 없음 (예보 데이터 부재)")

    hourly: dict[str, dict[str, str]] = defaultdict(dict)
    daily: dict[str, dict[str, str]] = defaultdict(dict)
    base_date = base_time = None

    for it in items:
        cat = it.get("category")
        if cat not in KEEP_CATEGORIES:
            continue
        fcst_date = it.get("fcstDate")
        fcst_time = it.get("fcstTime")
        value = str(it.get("fcstValue", ""))
        base_date = base_date or it.get("baseDate")
        base_time = base_time or it.get("baseTime")

        if cat in ("TMN", "TMX"):
            daily[fcst_date][cat] = value
        else:
            key = f"{fcst_date}T{fcst_time}"
            hourly[key][cat] = value

    return {
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
        "hourly": dict(hourly),
        "daily": dict(daily),
    }


async def fetch_now(
    *,
    service_key: str,
    nx: int,
    ny: int,
    tz: ZoneInfo,
    now: datetime | None = None,
) -> dict[str, Any]:
    """현재 시각 기준 직전 발표를 사용해 fetch."""
    now = now or datetime.now(tz)
    base_date, base_time = latest_base(now)
    log.info("KMA fetch base_date=%s base_time=%s nx=%d ny=%d", base_date, base_time, nx, ny)
    return await fetch_village_forecast(
        service_key=service_key, nx=nx, ny=ny,
        base_date=base_date, base_time=base_time,
    )
