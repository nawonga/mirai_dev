# Personal_Service OPERATING.md
# 퍼스널 서비스 운영 규칙

이 문서는 **Personal_Service**(개인 생활 보조 전문 지능 서비스)의 운영 규칙이다.

- 최상위 헌법: `/home/nawonga/MiraiProject/dev/OPERATING.md` (Mirai Space Constitution)
- 상위 오케스트레이션 문서: `/home/nawonga/MiraiProject/dev/Mirai_brain/OPERATING.md`

위 두 문서가 본 문서보다 우선하며, 충돌 시 상위 문서를 따른다.

---

## Document Status
- **Project Name:** Personal_Service
- **Orchestrator:** Mirai_brain (Gemini 2.5 Flash 기반 중앙 오케스트레이터)
- **Status:** Draft
- **Last Revised:** 2026-05-25 KST

---

## 1. 정체성 (Identity)

Personal_Service는 **독립적인 외부 도메인 모듈**이다.
Home_IoT / Aqua_DCS 와 동일하게 자체 디렉토리·독립 venv·자체 배포 경계를 가지며,
Mirai_brain 과는 **코드 결합 없이 표준 JSON 계약(REST)으로만** 연동한다.

- 개인화 지능 서비스의 '독립성'과 '재사용성'을 위해 외부 도메인으로 분리 유지한다.
- 현장 하드웨어(GPIO/센서/액추에이터)를 직접 제어하지 않는 **정보·일정 도메인**이다.
- Mirai_brain 에 코드 임포트되거나 인-프로세스로 흡수되지 않는다. (모노레포 통합 아님)

---

## 2. 역할 (Role)

개인 생활 보조 전문 지능 서비스. 사용자의 일상 정보 질의와 개인 일정/알림을 담당한다.

### 핵심 책임
1. **시간/날짜 조회** — 현재 시각, 날짜, 요일, 상대 시간(예: "3일 뒤") 계산.
2. **날씨 정보 브리핑** — 현재/예보 날씨를 사용자 친화적 멘트로 요약.
3. **알람 및 리마인더 관리** — 알람/리마인더 등록·조회·수정·취소, 예약 시점 도래 시 알림 트리거 데이터 제공.
4. Mirai_brain 이 확정한 요청을 실행하고, 개인 맞춤 결과를 표준 응답으로 반환.

### 제한 사항 (Boundaries)
- 직접적인 GPIO 제어, 센서 직접 읽기, 타 도메인(Home_IoT/Aqua_DCS) 직접 호출 금지.
- 사용자 의도의 1차 추정(STT/Local-First)은 Jarvis, 최종 의도 확정과 계획 수립은 Mirai_brain 책임이며, Personal_Service는 **확정된 정규화 명령을 실행**한다.
- 자연어 원문을 직접 해석하는 고차원 판단을 하지 않으며, 정규화된 JSON 요청만 처리한다.
- 타 도메인의 내부 안전 정책이나 최종 실행 책임을 대체하지 않는다.

---

## 3. 통신 및 호출 원칙 (Communication)

### 3.1 호출 경로
- Personal_Service는 **Mirai_brain 에 의해서만 호출**되는 외부 도메인 서비스다.
- Jarvis 가 Personal_Service 를 직접 호출하지 않는다. (계층적 단일 진입 경로 원칙: 모든 고차원 질의는 Mirai_brain 을 경유)
- 통신은 Mirai_brain ↔ Personal_Service 간 **REST API 표준 JSON 계약**으로 이루어진다.
- Local-First 원칙상 "지금 몇 시야?" 같은 초저위험·고정 질의는 Jarvis 로컬 규칙으로 즉시 처리될 수 있으며, 이때 Personal_Service 는 호출되지 않을 수 있다. Personal_Service 호출은 Mirai_brain 이 필요하다고 판단한 경우에 한정한다.

### 3.2 Base URL
`config/settings.yaml` 또는 Mirai_brain 측 integrations 설정에서 관리한다(예시):

```yaml
integrations:
  personal_service:
    base_url: "http://jm-pi:8100"
```

### 3.3 요청/응답 계약
미라이 스페이스 표준에 맞춰 **사용자 발화용 `message` 와 시스템 제어용 `data` 를 엄격히 분리**한다.

요청(envelope) 예시 — `POST /command`:
```json
{
  "domain": "personal_service",
  "operation": "get_time",
  "params": {},
  "request_id": "req-001",
  "plan_id": "plan-001",
  "trace_id": "trace-001",
  "source": "mirai_brain",
  "requester": "<human user>",
  "context": { "input_mode": "voice", "locale": "ko-KR" }
}
```

응답 예시:
```json
{
  "ok": true,
  "message": "지금은 오후 9시 32분이에요.",
  "data": {
    "operation": "get_time",
    "now": "2026-05-25T21:32:00+09:00",
    "request_id": "req-001",
    "trace_id": "trace-001"
  }
}
```

### 3.4 Operation 목록 (현재 / 계획)
| operation | 설명 | 비고 |
|---|---|---|
| `get_time` | 현재 시각/날짜/요일 조회 | 상대 시간 계산 포함 |
| `get_weather` | 현재/예보 날씨 브리핑 | 외부 날씨 API 연동 |
| `set_reminder` | 리마인더/알람 등록 | 시점·반복 규칙 포함 |
| `list_reminders` | 등록된 알람/리마인더 조회 | |
| `cancel_reminder` | 알람/리마인더 취소 | canonical id 기준 |
| `update_reminder`(계획) | 기존 항목 수정 | |

---

## 4. 추적성 및 기록 (Traceability & Logging)
- 모든 요청/응답은 `request_id`, `plan_id`, `trace_id` 를 보존하여 상위 Mirai_brain 요청과 연결 추적이 가능해야 한다.
- 실행 실패 및 사용자 의도 정정 발화는 디버깅·로컬 의도 추정 보조 데이터로 활용하기 위해 SQLite 감사 로그(Audit trail)에 누락 없이 기록한다.
- 알람/리마인더는 영속 저장소(SQLite 등)에 보관하여 재부팅·세션 단절 후에도 유지되어야 한다.

---

## 5. 안전 및 스케줄링 원칙
- 알람/리마인더 트리거 경로는 상위 AI 계층(Jarvis/Mirai_brain)의 일시 장애와 무관하게 예약 시점 데이터를 신뢰성 있게 보존해야 한다. (편의 기능이 데이터 무결성을 침범하지 않는다.)
- 예약 항목은 canonical id 로 식별하며, 음성 별칭(alias)은 의미 해석 보조 수단일 뿐 실행 기준이 아니다.
- 외부 날씨 API 등 네트워크 의존 기능은 실패 시 보수적으로 처리하고, 사용자에게 실패 사유를 명확한 `message` 로 전달한다.
- 상시 서비스 프로세스는 포그라운드 상시 실행을 금지하고 systemd 등으로 운영한다.

---

## 6. 개발/운영 격리 (Environment Separation)
- 모든 개발·패키지 설치·실험은 `dev` 환경에서 수행한다.
- `dev` 에서 검증된 코드만 `prod` 로 이관 배포한다.
- Personal_Service 는 독립 도메인 모듈로서 **자체 디렉토리와 독립 venv** 를 가진다. Mirai_brain 과 코드/형상을 공유하지 않는다.
- `.env` 의 API 키(날씨 API 등)는 코드에 하드코딩하거나 Git 커밋에 포함하지 않는다.

---

## 7. Revision Policy
- **2026-05-25 KST — Draft 신설**
  - Mirai_brain OPERATING.md 요구사항(시간/날짜, 날씨, 알람·리마인더) 기반으로 Personal_Service 운영 규칙 최초 정의.
  - Personal_Service 를 **독립적인 외부 도메인 모듈**로 규정 (Mirai_brain ↔ Personal_Service REST JSON 계약 연동).
