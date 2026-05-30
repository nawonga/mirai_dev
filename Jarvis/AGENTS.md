# AGENTS.md - Jarvis Router

Jarvis 작업 전에는 이 문서를 먼저 읽고, 이어서 최상위 `OPERATING.md` 및 Jarvis 전용 `OPERATING_RULES.md` 를 읽는다.

## 1) 프로젝트 역할
Jarvis는 음성 인터페이스, 로컬 우선 intent 추정, 상위 계층(Mirai_brain) 전달 게이트웨이다.
직접 설비 제어 시스템이나 Home_IOT 실행 주체가 되지 않는다.

상세 규칙:
- `OPERATING.md` (미라이 스페이스 전체 헌법)
- `OPERATING_RULES.md` (Jarvis 도메인 규칙)

## 2) canonical 경로
- 현재 개발 및 작업 경로 (Dev):
  - `/home/nawonga/MiraiProject/dev/jarvis`
- 실제 서비스 운영 경로 (Prod):
  - `/home/nawonga/MiraiProject/prod/jarvis`

클로드 코드는 반드시 **Dev 경로**에서만 작업하며, Prod 경로의 코드를 직접 수정하지 않는다.

## 3) 이 프로젝트에서 AI가 특히 기억할 것
- 상시 실행 방식은 `jarvis-prod.service` (또는 기존 host service) 기준이다.
- 실 로그 판단은 추측이 아니라 실제 로그 파일로 한다.
- 지연 기준은 wake detect가 아니라:
  - **사용자 발화 종료 시점(`record_done`) → Pepper 실제 발화 시작(`tts_start`)**
- 현재까지 확인된 바에 따르면 체감 지연의 주 병목은 STT/intent보다 **TTS** 였다.
- `TV 켜 줘` 류 문제는 STT 자체보다 `home_iot` 라우팅/intent 분류 실패 가능성을 먼저 본다.
- Porcupine은 유지하되 keyword 파일/설정 정합성을 실제 로그 기준으로 확인한다.

## 4) 반드시 먼저 볼 것
Jarvis 관련 작업 전 아래를 가능하면 먼저 확인한다.
- 실제 서비스 실행 경로 (Dev/Prod 확인)
- `config/settings.yaml`
- `data/logs/jarvis.log`
- 필요한 경우 `/var/log/jarvis.log` 또는 systemd 로그
- 현재 wakeword/intent/TTS 관련 최근 로그

### local-first / ruleset 1차 판단 관련 우선 참고 문서
Jarvis의 local-first 처리, 규칙 기반 1차 판단, Mirai_brain 2차 판단 힌트 전달 구조를 다루는 작업에서는 아래 문서를 먼저 확인한다.
- `OPERATING_RULES.md`
  - 특히 `6.1 Local-First Intent`
  - `6.2 Confidence Policy`
  - `6.3 Local-Only Intents`
  - `6.4 LLM Fallback Rule`
- `docs/setup/local_setup_rpi.md`
  - 상단의 `Jarvis는 local-first` 경로 설명

특히 다음 작업에서 우선 참고 대상이다:
- STT 이후 규칙셋/DB 기반 1차 intent 판단
- `불 켜`, `티비 켜` 같은 저지연 단순 명령 처리
- Jarvis가 Mirai_brain으로 넘기는 route hint / JSON payload 구조 조정
- Mirai_brain의 2차 판단 전제 수정
- Home_IOT / Personal_Service 등 실행 주체 분기 규칙 변경

## 5) 운영 메모
- `TIMING` / `TRACE` 라인이 남아야 latency 분석이 가능하다.
- weather/home_iot/wakeword 문제는 반드시 실제 샘플 로그 기준으로 판단한다.
- 경로가 엇갈려 보이면 코드 수정 전에 Dev/Prod 환경 분리 및 systemd 서비스 정합성을 먼저 확인한다.

## 6) 하지 말 것
- Jarvis가 Aqua-DCS/Home_IOT 책임을 침범하도록 구조를 바꾸지 말 것
- 경로 혼선을 덮기 위해 복사본 프로젝트를 새로 만들지 말 것
- 실서비스 로그 확인 없이 “원인 확정”하지 말 것