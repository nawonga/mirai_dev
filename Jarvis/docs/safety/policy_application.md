# Policy Application (Runtime)

이 문서는 Jarvis에서 **정책(Policy)이 실제로 어디서/어떤 순서로 적용되는지**를 고정합니다.

> 최우선 규칙은 `OPERATING_RULES.md` 입니다.

---

## 적용 위치

- 엔트리포인트: `src/jarvis/main.py`
- Intent 파싱 이후, 실제 실행(dispatch/LLM 호출) 이전에 정책을 통과해야 합니다.

---

## 적용 순서 (현재)

1) **Rate limit** (`src/jarvis/policies/rate_limit.py`)
   - 짧은 시간에 반복 호출되는 폭주를 방지

2) **Permissions** (`src/jarvis/policies/permissions.py`)
   - MVP에서는 `JARVIS_USER`(기본 `local`) 값이 비어있지 않은지만 체크
   - 향후 사용자/도메인/행동별 allowlist로 확장

3) **Safety** (`src/jarvis/policies/safety.py`)
   - 보수적으로 동작
   - 현재는 도메인 통합이 stub이므로, 물리 변경 가능성이 있는 intent는 기본 거부
     - `aqua_dcs`: `request_control`
     - `home_iot`: `turn_on`, `turn_off`

---

## 거부 처리

- 정책 거부 시:
  - 사용자에게 TTS로 거부 사유를 알려줌
  - SQLite audit log에 `REJECTED`로 기록

---

## 감사(Audit) 로그

- 저장소: `data/db/jarvis.db`
- 테이블: `command_logs`
- 기록 위치: `src/jarvis/main.py`
- 상태:
  - `APPROVED`: 정책 통과 후 응답 생성/발화까지 완료
  - `REJECTED`: 정책에서 차단됨

---

## TODO (다음 단계)

- aqua-dcs 상태(WARN/ERROR)를 조회하여 제어 거부에 반영
- rate-limit 정책을 사용자/도메인/행동별로 세분화
- permissions.yaml 등 외부 정책 정의 파일로 룰을 분리
