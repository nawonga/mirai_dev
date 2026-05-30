# Jarvis Text Command API (Inbound, Draft)

> 상태: **설계 초안 (미구현)**. 본 문서는 계약 정의이며 코드는 추후 구현한다.
> 최상위 규칙은 `OPERATING.md` 및 Jarvis `OPERATING_RULES.md`, 설계 기준은 `ARCHITECTURE.md`.

## 1. 목적

외부 시스템(예: **iOS 단축어**, 웹훅, 다른 스크립트)이 음성 없이 **텍스트 명령**을 Jarvis에 POST로 전달할 수 있는 **인바운드 REST 엔드포인트**를 정의한다.

- 기존 `aqua_dcs_api.md` 등은 Jarvis가 **클라이언트(요청자)**로 외부 도메인을 호출하는 계약이다.
- 본 문서는 반대로 Jarvis가 **서버**로서 외부의 텍스트 명령을 수신하는 계약이다.

## 2. 파이프라인 통합 원칙 (핵심)

들어온 텍스트는 **STT 출력과 동일한 것으로 간주**되어, 기존 음성 파이프라인의 **Intent 파싱 단계부터 그대로 재사용**된다.

```
[음성 경로]  Wakeword → Record → STT ─┐
                                      ├─→ Intent 파싱(Local-First) → Router → Domain → Policy → 응답
[텍스트 경로] POST /command (text) ───┘   (이 지점부터 두 경로는 완전히 동일)
```

- 텍스트 경로는 **Wakeword / Audio I/O / STT Layer만 건너뛴다.**
- Intent Layer 이후(Intent → Router → Domain → **Policy** → Storage)는 음성과 **동일 코드 경로**를 탄다.
- 즉 STT 결과 문자열을 만들어내는 대신, API 본문의 `text`를 그 자리에 주입(inject)한다.
- **Local-First 원칙 유지:** 단순 명령은 로컬 규칙으로 처리, 모호/복합 의도만 Mirai_brain으로 Fallback — 음성과 동일.
- **Policy Layer는 절대 우회하지 않는다.** 안전/권한/rate-limit은 텍스트 경로에도 동일하게 강제된다. (텍스트라고 안전 검사를 면제받지 않는다.)
- 응답은 TTS로 발화하는 대신, 호출자에게 텍스트(`message`)와 구조화 데이터(`data`)로 반환한다. (필요 시 옵션으로 로컬 TTS 발화도 트리거 가능 — 추후 결정)

## 3. 엔드포인트

### `POST /api/v1/command`

요청 헤더:
- `Content-Type: application/json`
- `Authorization: Bearer <JARVIS_API_TOKEN>` (인증 필수, §5 참고)

요청 바디:
```json
{
  "text": "거실 불 꺼줘",
  "source": "ios_shortcut",
  "user": "nawonga",
  "request_id": "ext-req-001",
  "locale": "ko-KR",
  "speak": false,
  "dry_run": false
}
```

| 필드 | 필수 | 설명 |
|---|---|---|
| `text` | ✅ | Intent 파싱에 태울 명령 문자열 (STT 출력 대체) |
| `source` | | 호출 출처 (`ios_shortcut`, `webhook`, `test` 등) — 감사 로그용 |
| `user` | | 요청 사용자 식별자 (권한/정책 판단 보조) |
| `request_id` | | 호출자 측 요청 id (없으면 서버가 생성). end-to-end 추적용 |
| `locale` | | 기본 `ko-KR` |
| `speak` | | true면 로컬 TTS로도 발화 (기본 false) |
| `dry_run` | | true면 intent 파싱까지만 수행하고 **실제 도메인 실행은 하지 않음** (테스트용) |

## 4. 응답

```json
{
  "ok": true,
  "message": "거실 불을 껐어요.",
  "data": {
    "intent": "home_iot.power_off",
    "entities": { "device": "living_room_light" },
    "route": "home_iot",
    "resolved_by": "local",
    "executed": true,
    "request_id": "ext-req-001",
    "trace_id": "trace-xyz"
  }
}
```

| 필드 | 설명 |
|---|---|
| `ok` | 처리 성공 여부 (boolean) |
| `message` | 사용자/호출자에게 보여줄 발화용 텍스트 |
| `data.intent` | 파싱된 intent (unknown 가능) |
| `data.resolved_by` | `local` / `mirai_brain` (어느 단계가 의도를 확정했는지) |
| `data.route` | 디스패치된 도메인 (`home_iot`, `aqua_dcs`, `personal_service`, `info` 등) |
| `data.executed` | 실제 도메인 실행 여부 (`dry_run`이면 false) |
| `data.request_id` / `data.trace_id` | 추적 식별자 |

오류 예시:
```json
{ "ok": false, "message": "이해하지 못했어요.", "data": { "intent": "unknown", "trace_id": "..." } }
```

상태 코드: 성공 200, 인증 실패 401, 바디 검증 실패 422, rate-limit 초과 429, 내부 오류 500.

## 5. 보안 / 운영 제약

외부에 노출되는 인바운드 엔드포인트이므로 다음을 **필수**로 한다.

- **인증:** `Authorization: Bearer <token>` 필수. 토큰은 `.env`로 관리하고 코드/깃에 하드코딩 금지.
- **바인딩:** 기본은 로컬/LAN 한정. 외부 인입이 필요하면 리버스 프록시(HTTPS) 뒤에 둔다. 평문 HTTP로 공인망에 직접 노출하지 않는다.
- **Rate-limit:** Policy Layer의 rate-limit을 텍스트 경로에도 적용. 연속/폭주 요청 차단.
- **감사 로그:** 모든 텍스트 명령은 음성 명령과 동일하게 Storage Layer(SQLite audit trail)에 기록한다 (`source`, `user`, `text`, 결과 포함).
- **안전 우선:** 도메인 안전 정책(특히 aqua-dcs ESD)을 우회/대체하지 않는다. Jarvis는 어디까지나 요청자다.

## 6. 비목표 (Non-Goals)
- 이 엔드포인트는 STT/Wakeword를 대체하지 않는다. 음성 경로와 **병행**하는 보조 인입 채널이다.
- GPIO/센서 직접 제어 없음 (`ARCHITECTURE.md` Hard Stops 동일 적용).

## 7. 구현 (2026-05-30 라이브 통과)

상태: **구현 완료**. 본 §은 실제 구현체 위치와 운영 형상을 기록한다.

- 코드: `src/jarvis/api.py` — `POST /api/v1/command`, Bearer 인증, `intent.parse()` 직접 호출 (음성 경로와 동일).
- 운영: systemd user service `jarvis-api.service` (port `8400`). dev 트리 정본 → `~/.config/systemd/user/` 심볼릭링크.
- 환경: `.env` 의 `JARVIS_API_TOKEN` (URL-safe 32B, `secrets.token_urlsafe(32)` 로 생성), `JARVIS_API_HOST=0.0.0.0`, `JARVIS_API_PORT=8400`.
- 의존성: `fastapi`, `uvicorn[standard]`, `pydantic`, `python-dotenv` (Jarvis venv).
- 라이브 통과 14 케이스 (CHANGELOG 2026-05-30 엔트리 참고): Local-first 4건, MB rule 4건, MB Gemini fallback 2건, dry_run 1건, 인증/검증 3건. "내일 우산 챙길까" → Gemini → `weather.tomorrow` → PS → 실 KMA 데이터 응답까지 음성 경로와 완전 동일.
- 미구현 (현재): `speak=true` 옵션 (Jarvis 데몬과 TTS 충돌 회피 위해 무시). audit trail (SQLite) — `system.audit_trail` 단계에서 통합 예정.

## 8. iOS 단축어 가이드

### 8.1 단축어 작성 (iOS Shortcuts 앱)

1. **단축어 앱** → **+** (새 단축어) → 이름: `향단아` (또는 원하는 호출명)
2. 액션 추가 순서:
   - **받아쓰기 (Dictate Text)** — 언어 한국어, "발화 중지 시 종료"
   - **URL** — `http://JM-PI.local:8400/api/v1/command` (또는 IP, 예: `http://192.168.0.x:8400/...`)
   - **URL 콘텐츠 가져오기 (Get Contents of URL)**:
     - 방법: **POST**
     - 헤더 추가:
       - `Authorization` : `Bearer <JARVIS_API_TOKEN 값>`
       - `Content-Type` : `application/json`
     - 요청 본문: **JSON**
       ```json
       {
         "text": [받아쓰기 결과],
         "source": "ios_shortcut",
         "user": "nawonga",
         "locale": "ko-KR"
       }
       ```
       *(받아쓰기 결과는 변수로 삽입)*
   - **사전 가져오기 (Get Dictionary from Input)** — 응답 JSON → Dictionary 로 변환
   - **사전 값 가져오기 (Get Dictionary Value)** — 키: `message`
   - **텍스트 말하기 (Speak Text)** — 위에서 가져온 `message` 를 Siri 음성으로 발화

### 8.2 사용 방법

> "**헤이 시리, 향단아**" → Siri 가 단축어 실행 → 받아쓰기 prompt → **"지금 몇시야"** → POST → 응답 message 를 Siri 가 발화

### 8.3 토큰 확인

JM-PI 에서:
```bash
grep '^JARVIS_API_TOKEN=' /home/nawonga/MiraiProject/dev/Jarvis/.env
```

### 8.4 네트워크 / 보안 고려

- 단축어가 LAN 안에서만 동작하면 `http://JM-PI.local:8400/...` (mDNS) 또는 LAN IP 사용. 평문 HTTP OK.
- 외부에서 호출하려면 **반드시 리버스 프록시 (HTTPS) 뒤에 두기**. 평문 HTTP 로 공인망 노출 금지.
- 토큰 재발급:
  ```bash
  NEW_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
  sed -i "s|^JARVIS_API_TOKEN=.*|JARVIS_API_TOKEN=$NEW_TOKEN|" /home/nawonga/MiraiProject/dev/Jarvis/.env
  systemctl --user restart jarvis-api.service
  # 새 토큰을 iOS 단축어의 Authorization 헤더에 반영
  ```

### 8.5 디버깅

JM-PI:
```bash
journalctl --user-unit jarvis-api.service -f          # 실시간 로그
curl -sf http://127.0.0.1:8400/healthz                # 데몬 상태
systemctl --user status jarvis-api.service
```

iOS:
- 단축어 액션 행마다 결과 확인 (실행 후 각 행 우측 정보 아이콘)
- HTTP 응답 코드 200 / 401 / 422 / 503 별 의미는 §4 참고

### 8.6 응답 시간 기대치 (LAN, 2026-05-30 측정)
- Local-first 명령 (시간/날짜/인사/sleep): **~15ms**
- MB rule (날씨/IoT): **~30~110ms**
- MB Gemini fallback (chitchat/의도 추론): **~1.5~2.1s**

총 사용자 체감 = `Siri 받아쓰기 (~1-2s) + 위 latency + Siri 발화`.
