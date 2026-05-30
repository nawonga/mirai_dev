# Mirai_brain — Milestones

상위 문서: [`OPERATING.md`](./OPERATING.md), [`dev/OPERATING.md`](../OPERATING.md).
하위 도메인: [`Personal_Service`](../Personal_Service/), [`Home_IOT`](../Home_IOT/), [`Aqua-DCS`](../Aqua-DCS/).

---

## M1 — 룰베이스 라우터 + Personal_Service 연동 (2026-05-29)

### 목표
- Jarvis 의 `mirai_brain.resolve()` 가 호출하는 단일 진입점 `POST /intent` 구현.
- Jarvis `Intent` 스키마(`{intent, route, entities, confidence, resolved_by, message}`) 와 정확히 호환되는 응답.
- 자연어 → (domain, operation, params) 룰베이스 분류 → Personal_Service `POST :8100/command` 호출 → message 회수.
- request_id/plan_id/trace_id 가 Jarvis → Mirai_brain → Personal_Service → 응답 → 역경로 전 구간 보존.

### 결과
- ✅ FastAPI(0.129.2)/httpx 기반 :8200. lifespan 부착, `/healthz` 확인.
- ✅ 룰베이스 라우터(`router.py`) — 키워드 기반 의도 분류 (날씨/시간/리마인더/미상). Gemini 통합은 후속 단계.
- ✅ Personal_Service 도메인 클라이언트(`domains/personal_service.py`) — envelope 표준 생성 + 5초 타임아웃 + DomainCallError graceful.
- ✅ 라이브 체인 7케이스 통과:
  - "지금 날씨 어때?" → weather.now → `"현재 강동구 고덕동 기온은 28도예요. 하늘은 맑음이에요. 습도는 35%예요."`
  - "오늘 날씨 알려줘" → weather.today → `"...최저 20도, 최고 28도..."`
  - "내일 비 와?" → weather.tomorrow → `"...최저 16도, 최고 29도..."`
  - "지금 강동구 기온이 어때?" → weather.now (동일)
  - "지금 몇시야?" (Mirai_brain 경유 케이스) → time.now → `"지금은 오후 3시 14분이에요."`
  - "내일 아침 7시 알람 맞춰줘" → reminder.placeholder → set_reminder (planned) → `"해당 기능은 아직 준비 중이에요."` ok=false
  - "오늘 저녁 뭐 먹지" → unknown (도메인 호출 없음) → 안내 멘트
- ✅ trace_id propagation 검증 — 도메인 호출 경로는 모두 전달, unknown 케이스는 도메인 호출 자체가 없으므로 미생성.
- ✅ **Jarvis CLI 통합 검증** (`PYTHONPATH=src python -m jarvis.intent "지금 날씨 어때?"`):
  - 날씨/내일비 → route=personal_service, resolved_by=mirai_brain.router+personal_service, message=실 KMA 데이터
  - 시간 → **route=local, by=local** (Jarvis Local-First 가 핸드오버 차단 — OPERATING.md §6 준수)
  - unknown → route=mirai_brain, graceful 응답

### 변경/신설 파일
- `src/mirai_brain/__init__.py`
- `src/mirai_brain/router.py` — `RoutedIntent`, `parse(text)` 키워드 매칭.
- `src/mirai_brain/domains/__init__.py`
- `src/mirai_brain/domains/personal_service.py` — `call_command()` 비동기 httpx 클라이언트 + `new_ids()` request_id/plan_id 생성.
- `src/mirai_brain/main.py` — FastAPI app, `POST /intent`, `IntentRequest`/`IntentResponse` Pydantic 모델 (Jarvis 호환).
- `requirements.txt` — fastapi/uvicorn/pydantic/python-dotenv/httpx.
- `.env` — `MB_HOST=0.0.0.0`, `MB_PORT=8200`, `PERSONAL_SERVICE_URL=http://127.0.0.1:8100`.
- `.gitignore`.
- `Jarvis/.env` 갱신 — `MIRAI_BRAIN_URL=http://127.0.0.1:8200` 추가.

### 실행 방법
```bash
# 1) Personal_Service 기동 (:8100)
cd /home/nawonga/MiraiProject/dev/Personal_Service
PYTHONPATH=src venv/bin/uvicorn personal_service.main:app --host 0.0.0.0 --port 8100

# 2) Mirai_brain 기동 (:8200)
cd /home/nawonga/MiraiProject/dev/Mirai_brain
PYTHONPATH=src venv/bin/uvicorn mirai_brain.main:app --host 0.0.0.0 --port 8200

# 3) Jarvis CLI 핸드오버 테스트
cd /home/nawonga/MiraiProject/dev/Jarvis
PYTHONPATH=src venv/bin/python -m jarvis.intent "내일 비 와?"
```

### 다음 단계
- **Aqua_DCS 도메인 클라이언트** — `domains/aqua_dcs.py`. 모니터링 상태 조회 등.
- **Audit trail (SQLite)** — OPERATING.md §개발원칙. 요청/계획/응답을 trace_id 기준 누적.
- **컨텍스트/멀티턴** — Gemini 호출에 직전 대화 컨텍스트 첨부.
- **Jarvis 음성 E2E** — 마이크 발화 한 번으로 STT → MB → HIOT → TTS 까지 통과.

---

## M4 — systemd 3-tier 상시 운영 도입 (2026-05-29)

### 목표
- PS + HIOT + MB 를 systemd 로 supervise → 부팅 시 자동 기동, 크래시/킬 시 자동 재시작.
- OPERATING.md §5 "상시 서비스 프로세스는 포그라운드 상시 실행을 금지하고 systemd 등으로 운영" 충족.
- Dev 트리를 정본으로 두고 `/etc/systemd/system/` 으로 심볼릭링크 → 편집·롤백이 dev 에서만 일어남.

### 결과 (2026-05-29 21:02 KST, JM-PI 본기)
- ✅ unit 파일 3개 작성 (각 프로젝트 `systemd/*.service`):
  - `personal_service.service` (port 8100, ReadWritePaths=storage)
  - `home_iot.service` (port 8300, ReadWritePaths=storage, SupplementaryGroups=dialout for Zigbee)
  - `mirai_brain.service` (port 8200, After/Wants=personal_service home_iot)
- ✅ 공통 정책: `Type=simple`, `User=nawonga`, `EnvironmentFile=<proj>/.env`, `PYTHONPATH=src`, `Restart=on-failure`, `RestartSec=5`, 약한 sandbox(`NoNewPrivileges`/`ProtectSystem=full`/`ProtectHome=read-only`).
- ✅ 설치 스크립트 `dev/systemd/install.sh` — 심볼릭링크 + daemon-reload + enable + start.
- ✅ 부팅 자동 기동 (`is-enabled = enabled` × 3).
- ✅ **자동 재시작 라이브 검증**: PS 메인 프로세스 `kill -9` → 5초 안에 새 PID 로 재기동 (`NRestarts: 1`), 캐시 파일(`storage/weather_cache.json`) 영속 보존 → 재시작 후 즉시 `healthz` 200 + `/intent` E2E 정상.
- ✅ **의존성 체인 검증**: `systemctl restart mirai_brain` → MB 단독 재기동, PS/HIOT 손대지 않음 → 다시 `거실 불 꺼줘` 실행 정상.
- ✅ 로그 일원화: `journalctl -u <name>.service [-f]` 로 모든 서비스 로그 통합 조회. `SyslogIdentifier` 으로 grep 가능.
- ✅ 부팅 시 PS 가 캐시 자동 갱신 (e.g., 부팅 후 다음 갱신 23:15 예약).

### 변경/신설 파일
- `dev/Personal_Service/systemd/personal_service.service`
- `dev/Home_IOT/systemd/home_iot.service`
- `dev/Mirai_brain/systemd/mirai_brain.service`
- `dev/systemd/install.sh` (실행 권한 부여)
- `/etc/systemd/system/{personal_service,home_iot,mirai_brain}.service` — dev 트리로 심볼릭링크

### 운영 명령
```bash
# 상태 (sudo 불필요)
systemctl status personal_service home_iot mirai_brain
systemctl is-active personal_service     # active / failed / inactive

# 로그 (실시간 / 최근 N줄)
journalctl -u mirai_brain.service -f
journalctl -u personal_service.service -n 50

# 수동 제어 (sudo 필요)
sudo systemctl restart mirai_brain.service
sudo systemctl stop home_iot.service
sudo systemctl reload-or-restart mirai_brain.service

# unit 파일 수정 후 (dev 트리 정본 편집)
sudo systemctl daemon-reload && sudo systemctl restart <name>

# 제거
sudo systemctl disable --now mirai_brain personal_service home_iot
sudo rm /etc/systemd/system/{mirai_brain,personal_service,home_iot}.service
sudo systemctl daemon-reload
```

### 트러블슈팅
- **`a terminal is required to read the password`**: Claude Code `!` 명령은 TTY 없어 sudo 비번 못 받음. **별도 SSH/로컬 터미널에서 `sudo bash install.sh`** 실행해야 함. 이후 검증 명령은 sudo 불필요라 이 세션에서 그대로 수행.
- **포트 충돌**: `ss -ltn 'sport = :8100 or sport = :8200 or sport = :8300'` 으로 확인. 수동 uvicorn 잔여 프로세스가 있으면 systemd 시작 실패. `pgrep -f venv/bin/uvicorn` 으로 확인 후 kill.
- **`.env` 형식**: systemd `EnvironmentFile=` 은 KEY=VALUE 만 허용. 다중 라인·따옴표 사용 시 거부. 우리 `.env` 들은 모두 호환됨 (사전 검증).

---

## M3 — Home_IOT 도메인 클라이언트 (2026-05-29)

### 목표
- Home_IOT 를 HTTP-접근 가능 도메인으로 노출 (`engine.handle_json` 의 FastAPI 래퍼).
- Mirai_brain 라우터에 IoT 룰(켜기/끄기/상태/목록) 추가.
- Gemini 화이트리스트 + 시스템 프롬프트에 home_iot operation 추가.
- 룰베이스 단순 발화 + Gemini 우회/복합 발화 모두 도메인까지 라우팅.

### 결과 (2026-05-29 20:31 KST, 라이브)
- ✅ **Home_IOT FastAPI 래퍼** (`src/home_iot/api.py`) `POST /command`/ `GET /healthz`, lifespan 에서 registry 로드. CLI/stdin (`main.py handle-json`) 과 함께 두 진입점 공존. 응답 envelope 은 기존 `engine.handle_json` 그대로 (`{ok, message, data}` — PS와 호환).
- ✅ **MB 도메인 클라이언트** (`domains/home_iot.py`) — 비동기 httpx, envelope 표준 (device_id/action/추적자).
- ✅ **MB 라우터** (`router.py`) — `_route_home_iot()`: 목록·상태·켜기·끄기 룰 + `_looks_compound()` 으로 복합 명령은 Gemini 로 escalate. 정중 어미 정규식(`_POLITE_TAIL_RE`)으로 "X 알려 줘"/"X 어때" 패턴까지 깔끔히 device 추출.
- ✅ **MB Gemini fallback** (`gemini.py`) — `ALLOWED_OPERATIONS["home_iot"] = {list_devices, list_actions, execute_action, get_status}`. SYSTEM_INSTRUCTION 에 등록된 alias 표(TV/거실 조명/에어컨)와 action 토큰 명세, 복합 명령은 한 동작만 실행 + 안내 가이드.
- ✅ **3-tier 라이브 검증**:
  - 룰베이스 7건 모두 22~48ms:
    - "거실 불 켜줘/꺼줘" → power_on/power_off
    - "에어컨 켜" → power (aircon은 토글만 보유)
    - "TV 상태 알려줘" / "에어컨 어때?" → get_status
    - "기기 목록 알려줘" → list_devices
  - Gemini fallback 4건 1.5~2.9s:
    - "거실 조명 끄고 에어컨도 꺼줘" → 복합 감지 → 룰 escalate → Gemini → 거실 조명 우선 끄기 (안내 reasoning)
    - "TV 켜고 거실 불 꺼줘" → 동일 패턴 → TV 우선 power
    - "TV 소리 좀 키워줘" → Gemini → volume_up 실행
    - "방이 좀 어두운데" → chitchat.feeling (보수적 분류) — OPERATING.md "확정된 명령" 원칙에 부합
  - PS 회귀 통과: "내일 비 와?" 25ms, "지금 몇시야?" 25ms.

### 변경/신설 파일
- `Home_IOT/src/home_iot/api.py` 신설 — FastAPI 래퍼.
- `Home_IOT/requirements.txt` — fastapi/uvicorn/pydantic/python-dotenv 추가.
- `Home_IOT/.env` — `HI_HOST=0.0.0.0`, `HI_PORT=8300`.
- `Mirai_brain/src/mirai_brain/domains/home_iot.py` 신설.
- `Mirai_brain/src/mirai_brain/router.py` — `_route_home_iot`, `_POLITE_TAIL_RE`, `_COMPOUND_RE`, `_looks_compound`.
- `Mirai_brain/src/mirai_brain/gemini.py` — `ALLOWED_OPERATIONS` home_iot 추가, SYSTEM_INSTRUCTION 갱신.
- `Mirai_brain/src/mirai_brain/main.py` — `_dispatch_home_iot()`, home_iot 분기 (룰+Gemini). 버전 0.3.0.
- `Mirai_brain/.env` — `HOME_IOT_URL=http://127.0.0.1:8300`.

### 실행
```bash
# 3-tier 기동 (절대 경로 cd 필수)
(cd /home/nawonga/MiraiProject/dev/Personal_Service && PYTHONPATH=src venv/bin/uvicorn personal_service.main:app --host 0.0.0.0 --port 8100) &
(cd /home/nawonga/MiraiProject/dev/Home_IOT        && PYTHONPATH=src venv/bin/uvicorn home_iot.api:app           --host 0.0.0.0 --port 8300) &
(cd /home/nawonga/MiraiProject/dev/Mirai_brain     && PYTHONPATH=src venv/bin/uvicorn mirai_brain.main:app       --host 0.0.0.0 --port 8200) &

# 사용자 발화 시뮬레이션
curl -X POST :8200/intent -d '{"text":"거실 불 켜줘"}'
curl -X POST :8200/intent -d '{"text":"TV 켜고 거실 불 꺼줘"}'  # Gemini 경로
```

### 알려진 한계
- **복합 명령**: 현재 한 동작만 실행 (Gemini 가 가장 중요한 것 선택). 두 동작 모두 실행하려면 multi-action 지원 (operation 배열) 도입 필요 — 향후 단계.
- **Alias 정확성**: Gemini 가 alias 가이드를 따르지 않고 "거실 TV" 등 자유 표현을 보낼 수 있음 (현재는 alias matching 의 normalize 가 일부 흡수). 동적으로 registry 에서 alias 받아 프롬프트에 주입하는 것이 깔끔.

### 트러블슈팅
- **포트 충돌**: 워커 프로세스가 `kill <PID>` 로 안 죽음 — uvicorn 의 master/worker 분리 때문. `pgrep -f "venv/bin/uvicorn"` 으로 모든 자식 찾아 kill.
- **`거실 TV 기기를 찾지 못했어요`**: Gemini 가 자유 표현을 사용한 케이스. 시스템 프롬프트의 alias 표 확인.
- **룰베이스가 복합 명령을 잘못 매칭**: `_looks_compound()` 패턴 보강 (`끄고|켜고|꺼서|켜서` 등).

---

## M2 — Gemini 2.5 Flash fallback (2026-05-29)

### 목표
- 룰베이스로 분류 불가능한 모호/우회 발화 (예: "내일 우산 챙길까?", "오늘 저녁 뭐 먹지") 를 Gemini 가 처리.
- 라우팅 가능 의도는 알려진 operation 으로 분류 후 도메인 호출, 그 외는 conversational message 직접 반환.
- 알려지지 않은 operation 호출 금지 (화이트리스트 강제).
- thinking_budget=0 으로 응답 지연 최소화.

### 결과 (2026-05-29 19:36 KST, 라이브)
- ✅ `gemini.py` — `google-genai` SDK + 비동기 `classify()`. `response_mime_type=application/json` + `system_instruction` (도메인/operation 명세 + JSON 스키마 강제). `ThinkingConfig(thinking_budget=0)` 적용.
- ✅ `ALLOWED_OPERATIONS` 화이트리스트 — Gemini가 미허용 operation 제안 시 자동 chitchat 강등.
- ✅ `WEATHER_WHEN_ALIASES` — Gemini 가 "현재"/"지금" 같이 한국어로 답해도 PS 가 받는 `now/today/tomorrow` 로 정규화.
- ✅ 라우팅 순서 = 룰베이스 우선, `domain="none"` 일 때만 Gemini fallback (불필요한 클라우드 호출 회피).
- ✅ **9 케이스 라이브 통과**:
  - 룰베이스 4건 모두 25~68ms (Gemini 미호출): weather.now/tomorrow, time.now, reminder.planned.
  - Gemini 5건 모두 1.4~2.0s:
    - "**내일 우산 챙길까?**" → Gemini → `weather.tomorrow` → PS → 실 KMA `"내일 강동구 고덕동... 최저 17도, 최고 29도..."` ← **2차 인텐트 분석 핵심 시연**
    - "오늘 저녁 뭐 먹지" → chitchat.suggestion → "오늘은 어떤 음식이 당기시나요?..."
    - "기분이 좀 그래" → chitchat.mood → "무슨 일 있으신가요? 제가 기분 전환에..."
    - "이번 주말 야외 활동하기 좋아?" → chitchat.question → "주말 날씨는 아직 알 수 없지만..." (Gemini 가 PS의 `when` 한계 인지하고 솔직히 안내)
    - "라즈베리파이가 뭐야?" → chitchat.definition → "신용카드 크기만한 작은 컴퓨터예요..."
- ✅ healthz 가 `gemini: true/false` 노출 — 키 활성 여부 즉시 확인.
- ✅ graceful degradation: 키 미설정 시 SDK 초기화 스킵, fallback 멘트 그대로.

### 변경/신설 파일
- `src/mirai_brain/gemini.py` — `GeminiClient` (비동기), `GeminiResult`, `ALLOWED_OPERATIONS`, `WEATHER_WHEN_ALIASES`, `SYSTEM_INSTRUCTION`, `_enforce_whitelist()`.
- `src/mirai_brain/main.py` — lifespan 에서 GeminiClient 초기화, `domain == "none"` 분기에 Gemini fallback 통합. 버전 0.2.0.
- `requirements.txt` — `google-genai>=1.0,<2.0`.
- `.env` — `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-2.5-flash`.

### 실행 / 검증
```bash
# 부팅 (절대 경로로 cd — 같은 venv 이름이라 cwd 오타에 주의)
(cd /home/nawonga/MiraiProject/dev/Personal_Service && PYTHONPATH=src venv/bin/uvicorn personal_service.main:app --host 0.0.0.0 --port 8100) &
(cd /home/nawonga/MiraiProject/dev/Mirai_brain   && PYTHONPATH=src venv/bin/uvicorn mirai_brain.main:app   --host 0.0.0.0 --port 8200) &

# healthz (Gemini 활성 여부)
curl -s http://127.0.0.1:8200/healthz   # {"ok":true,...,"gemini":true}

# 룰베이스 — ms 단위
curl -X POST :8200/intent -d '{"text":"내일 비 와?"}'

# Gemini fallback — 1~2초
curl -X POST :8200/intent -d '{"text":"내일 우산 챙길까?"}'
```

### 트러블슈팅
- **`gemini: false`**: `.env` 의 `GEMINI_API_KEY` 미설정 / `google-genai` 미설치 / SDK 초기화 실패. 서버 부팅 로그 확인 (`lifespan up: ... gemini=disabled`).
- **응답 latency 3~5초**: `thinking_budget=0` 누락 또는 SDK 가 무시. `gemini.py` 의 `ThinkingConfig` 인자 확인.
- **Gemini 가 새로운 operation 만들어냄**: `ALLOWED_OPERATIONS` 화이트리스트가 chitchat 으로 강등. 로그에 `미허용 operation 제안` 경고.
- **이상한 weather `when`**: `WEATHER_WHEN_ALIASES` 가 정규화. 매핑되지 않는 값은 `now` 로 fallback.
- **포트 충돌 (`address already in use`)**: 이전 세션 PS/MB 가 살아있음. `pgrep -af uvicorn` 으로 확인 후 PID 명시 kill.

### 트러블슈팅
- **`MIRAI_BRAIN_URL` 미설정**: Jarvis `mirai_brain.py` 가 스텁("아직 그 요청은 제가 처리하지 못해요") 반환. `.env` 확인.
- **Personal_Service 미가동**: Mirai_brain 가 `DomainCallError` → `"죄송해요, 지금은 그 정보를 가져올 수 없어요."` 안내. PS :8100 healthz 먼저 확인.
- **응답 타임아웃**: 기본 5초. KMA 캐시 hit이면 ms 단위. KMA 신규 fetch 가 끼면 200~500ms.
