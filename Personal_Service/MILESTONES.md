# Personal_Service — Milestones

이 문서는 **세션이 끊기거나 새 세션에서 다시 작업을 이어갈 때** 빠르게 맥락을 복구하기 위한 마일스톤 로그다.

규칙:
- 마일스톤마다 **목표 / 결과 / 변경 파일 / 실행 방법 / 다음 단계**를 기록한다.

상위 문서: [`OPERATING.md`](./OPERATING.md), [`dev/OPERATING.md`](../OPERATING.md), [`dev/Mirai_brain/OPERATING.md`](../Mirai_brain/OPERATING.md).

---

## M1 — FastAPI 골격 + `get_time` operation (2026-05-29)

### 목표
- OPERATING.md §3.3 표준 envelope를 단일 진입점 `POST /command` 로 노출하는 최소 FastAPI 서비스 기동.
- 5개 operation 중 `get_time` 하나를 실제 동작시키고, 나머지는 graceful 미구현 응답으로 라우팅.
- 라이브 검증으로 envelope 추적자(`request_id`/`plan_id`/`trace_id`)가 응답 `data` 에 보존됨을 확인.

### 결과
- ✅ FastAPI(0.129.2) + uvicorn(0.44.0) + pydantic(2.13.4) venv 설치, 127.0.0.1:8100 기동.
- ✅ `get_time` 6가지 케이스 라이브 검증 통과:
  1. 기본 호출 → `"오늘은 2026년 5월 29일 금요일, 오후 1시 42분이에요."`
  2. `field=time` → `"지금은 오후 1시 42분이에요."` (OPERATING.md 예시와 동일 톤)
  3. `offset_days=3, field=date` → `"3일 뒤는 2026년 6월 1일이에요."` (상대 시간 계산 동작)
  4. `get_weather`(planned but unimplemented) → `ok:false`, `"해당 기능은 아직 준비 중이에요."`
  5. `fly_to_mars`(unknown) → `ok:false`, `"요청하신 동작을 이해하지 못했어요."`
  6. `field=bogus`(ValueError) → `ok:false`, `"요청 형식이 올바르지 않아요."`
- ✅ 모든 응답 `data` 에 `operation/request_id/plan_id?/trace_id?` 보존.
- ✅ 타임존 `Asia/Seoul` 고정(`.env` PS_TIMEZONE), 응답 `data.now/target` 는 ISO 8601 `+09:00`.

### 변경/신설 파일
- `requirements.txt` — fastapi/uvicorn[standard]/pydantic/python-dotenv (보수적 범위 핀)
- `.env` — `PS_HOST/PS_PORT/PS_LOCALE/PS_TIMEZONE` (gitignore)
- `.gitignore` — `.env`, `venv/`, 캐시, 향후 SQLite DB 경로
- `src/personal_service/__init__.py`
- `src/personal_service/contracts.py` — `CommandRequest/CommandResponse` Pydantic 모델 (envelope §3.3)
- `src/personal_service/main.py` — FastAPI app, `POST /command` 디스패처, `GET /healthz`
- `src/personal_service/operations/__init__.py`
- `src/personal_service/operations/get_time.py` — `field` × `offset_days` 조합으로 한국어 message 생성

### 실행 방법
```bash
cd /home/nawonga/MiraiProject/dev/Personal_Service
PYTHONPATH=src venv/bin/uvicorn personal_service.main:app --host 0.0.0.0 --port 8100
```

검증:
```bash
curl -s http://127.0.0.1:8100/healthz
curl -s -X POST http://127.0.0.1:8100/command \
  -H 'Content-Type: application/json' \
  -d '{"domain":"personal_service","operation":"get_time","params":{},"request_id":"req-001"}'
```

### 다음 단계
- **M3 — 리마인더**: SQLite 영속 저장소 스키마 설계, `set_reminder/list_reminders/cancel_reminder` 구현. 트리거 경로(스케줄러)는 별도 결정 필요(systemd timer vs 인프로세스 APScheduler).
- **운영 이관**: systemd unit 작성 → `prod/Personal_Service` 동기화 (OPERATING.md §5 상시 서비스 원칙).
- **추적성 보강**: SQLite Audit trail (OPERATING.md §4) — operation 단위 요청/응답 로그.

---

## M2 — `get_weather` (KMA 단기예보 + 3시간 캐시) (2026-05-29)

### 목표
- KMA 단기예보(`getVilageFcst`) 를 백그라운드로 3시간마다 fetch 하여 캐시.
- Jarvis → Mirai_brain → Personal_Service 경로로 `get_weather` 호출 시 캐시 데이터를 한국어 자연어로 응답.
- 키 미설정·fetch 실패에서도 서비스가 죽지 않고 보수 응답 (OPERATING.md §5).

### 결과
- ✅ httpx + asyncio 기반 인-프로세스 스케줄러. FastAPI lifespan 에서 시작·종료.
- ✅ 갱신 트리거 = `latest_base()` / `next_fetch_time()`: KMA 발표시각(02/05/08/11/14/17/20/23시) + 15분 마진.
- ✅ 캐시 = `storage/weather_cache.json` 원자적 쓰기(tmp + os.replace). `is_stale()` 는 TTL(3.5h) 또는 다음 발표시각 도래로 판정.
- ✅ 격자 변환 함수 (LCC) 정합 검증 — 서울 시청 (37.5665,126.9780) → nx=60, ny=127 KMA 표 일치.
- ✅ Mock 캐시 dry-run 으로 포매터 검증:
  - `when=now` → `"현재 강동구 고덕동 기온은 21도예요. 하늘은 맑음이에요. 습도는 45%예요."`
  - `when=today` → `"오늘 강동구 고덕동 날씨를 알려드릴게요. 하늘은 전반적으로 맑음이에요. 최저 14도, 최고 23도예요. 강수 확률은 최대 30%예요."`
  - `when=tomorrow` → `"내일 강동구 고덕동 날씨를 알려드릴게요. 하늘은 전반적으로 구름 많음이에요. 최저 13도, 최고 19도예요. 비 예보가 있어요."`
- ✅ 키 미설정 경로: `get_weather` → `ok:false`, `"날씨 서비스가 아직 설정되지 않았어요."`. `/admin/refresh-weather` → 503.
- ✅ 회귀: `get_time` 정상.
- ✅ **라이브 검증 완료 (2026-05-29 14:45 KST)**:
  - 인증: **기상청 API 허브 (apihub.kma.go.kr)** authKey. data.go.kr 가 아닌 apihub 게이트웨이 사용 (호스트 + 파라미터명 변경 반영). VilageFcstInfoService_2.0 활용신청 승인 받음.
  - 부팅 fetch HTTP 200 → 캐시 base=`20260529/1400`, hourly=**66**, daily=**3** (5/30·5/31·6/1).
  - `when=now`: `"현재 강동구 고덕동 기온은 28도예요. 하늘은 맑음이에요. 습도는 35%예요."` (실 데이터)
  - `when=today`: `"오늘 강동구 고덕동 날씨를 알려드릴게요. 하늘은 전반적으로 맑음이에요. 최저 20도, 최고 28도예요. 강수 가능성은 낮아요."`
  - `when=tomorrow`: `"내일 강동구 고덕동 날씨를 알려드릴게요. 하늘은 전반적으로 맑음이에요. 최저 16도, 최고 29도예요. 강수 가능성은 낮아요."` (5/30 TMN=16, TMX=29)
  - 다음 자동 갱신 17:15 (KMA 발표 + 15분 마진) 스케줄 등록 확인.
  - `request_id`/`plan_id`/`trace_id` 모두 응답 `data` 에 보존.

### 변경/신설 파일
- `src/personal_service/weather/__init__.py`
- `src/personal_service/weather/grid.py` — KMA LCC 양방향 변환 + CLI (`python -m personal_service.weather.grid --to-grid LAT LON`).
- `src/personal_service/weather/kma_client.py` — `fetch_village_forecast`, `latest_base`, `next_fetch_time`, 응답 파싱 → 시간별/일별 버킷.
- `src/personal_service/weather/cache.py` — `WeatherCache` (디스크 atomic write, asyncio.Lock), `CacheEntry.is_stale()`.
- `src/personal_service/weather/scheduler.py` — `WeatherScheduler` (부팅 즉시 fetch + 다음 base+margin sleep, 실패 시 10분 백오프).
- `src/personal_service/weather/formatter.py` — `when` 별 완결 문장 조립.
- `src/personal_service/operations/get_weather.py` — operation 핸들러 `(ok, message, data)` 반환.
- `src/personal_service/main.py` — lifespan 통합, `get_weather` 디스패치, `POST /admin/refresh-weather`. 버전 0.2.0.
- `.env` — `KMA_SERVICE_KEY`(빈 값), `WEATHER_LOCATION_NX/NY/NAME`(강동구 고덕동 62/126), `WEATHER_CACHE_PATH`.
- `.gitignore` — `storage/*.json`, `storage/.weather_cache_*` 추적 제외.
- `requirements.txt` — `httpx>=0.27,<0.29` 추가.

### 실행 방법
```bash
cd /home/nawonga/MiraiProject/dev/Personal_Service
# 키 설정 (한 번)
sed -i 's/^KMA_SERVICE_KEY=.*/KMA_SERVICE_KEY=<발급받은 Decoding 키>/' .env
# 기동
PYTHONPATH=src venv/bin/uvicorn personal_service.main:app --host 0.0.0.0 --port 8100
# 수동 즉시 fetch
curl -X POST http://127.0.0.1:8100/admin/refresh-weather
# 사용자 질의
curl -X POST http://127.0.0.1:8100/command -H 'Content-Type: application/json' \
  -d '{"domain":"personal_service","operation":"get_weather","params":{"when":"now"},"request_id":"r1"}'
```

### 트러블슈팅
- **HTTP 401 Unauthorized**: data.go.kr 호스트로 호출한 경우. 우리는 **apihub.kma.go.kr** 사용. 호스트와 인증 파라미터 (`authKey`) 확인.
- **HTTP 403 `활용신청이 필요한 API 입니다`**: apihub 는 **operation 단위로 개별 활용신청**. VilageFcstInfoService_2.0 안의 getUltraSrtNcst/getUltraSrtFcst/getVilageFcst 각각 신청해야 함.
- **응답이 XML 로 옴**: KMA 서버가 키 미등록/오타 시 에러 XML/text 반환. `kma_client._parse_response` 에서 JSON 강제 검사 후 `KmaError` 로 surface.
- **stale 경고가 응답에 붙음**: 마지막 fetch 후 다음 KMA 발표시각이 도래했는데 우리가 새 데이터를 못 받았다는 신호. 스케줄러 로그 확인.
- **격자 좌표 의심**: `python -m personal_service.weather.grid --to-grid <lat> <lon>` 으로 재계산.
