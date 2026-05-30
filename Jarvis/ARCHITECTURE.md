# Jarvis Architecture

Jarvis(일명 **Pepper Potts**)는 **한국어 음성 기반의 로컬-퍼스트 오케스트레이터**입니다.

> 목표: Wakeword → TTS → Record → STT → Intent → Domain → Response

이 문서는 코드 변경과 독립적인 **설계 헌법(Architecture Constitution)** 입니다.
구현 세부(파라미터/명령어)는 `RECOVERY_GUIDE.md`, `README_LOCAL_SETUP.md`, `MILESTONES.md`를 참고합니다.

---

## 1) 역할 정의 (Boundaries)

### Jarvis
- 사람 인터페이스 + 오케스트레이터
- 음성 입력을 텍스트로 변환(STT)하고, 의도(intent)를 파싱해 라우팅하고,
  각 도메인(domain)의 작업을 실행한 뒤 음성(TTS)으로 응답합니다.

### aqua-dcs / home_iot
- 설비 제어 시스템(수조의 뇌와 손, 스마트홈 실행 엔진)
- 센서/액추에이터/ESD(안전 로직) 등 **현장 안전/제어의 단일 권한자**

### Mirai_brain
- 시스템의 최상위 오케스트레이션 및 AI 의미 해석 계층 (Gemini 2.5 Flash 기반)

### 통신
- Jarvis ↔ aqua-dcs 및 home_iot는 **REST API 계약**으로만 통신합니다.
- Jarvis는 GPIO/센서/액추에이터를 직접 제어하지 않습니다.

---

## 2) 레이어 구조

아래 레이어는 분리되어야 하며, 상위 레이어가 하위 레이어 구현 세부를 침범하지 않습니다.

1. **Wakeword Layer**: 웨이크워드 감지 (Porcupine)
2. **Audio I/O Layer**: 녹음/재생 (ALSA/PipeWire)
3. **STT Layer**: faster-whisper 로컬 전사
4. **Intent Layer**: 로컬 rule-based intent 파서 (+ 필요시 Mirai_brain 전달)
5. **Router Layer**: intent → domain action 디스패치
6. **Domain Layer**: 실제 기능 구현 (aqua_dcs, home_iot, info, personal_device)
7. **Policy Layer**: safety / permissions / rate-limit (모든 실행 경로에 강제)
8. **Storage Layer**: audit trail (SQLite)
9. **Jobs Layer(선택)**: 오래 걸리는 비동기 작업

---

## 3) 절대 금지 사항 (Hard Stops)

구체 규칙은 `OPERATING_RULES.md`가 우선합니다.

- GPIO 직접 제어 금지
- 센서 직접 읽기 금지(특히 aqua-dcs의 센서/제어 경로 침범 금지)
- aqua-dcs 안전 로직(ESD)을 대체하는 판단 금지
- 런타임 경로에서 장시간 블로킹 AI 호출 금지

---

## 4) 데이터/코드/설정 분리

- **코드**: `src/`
- **실데이터**: `data/` (db/logs/cache/models)
- **설정**: `config/` (settings.yaml이 single source of truth)

---

## 5) 엔트리포인트 런타임 플로우(현재)

현재 기본 플로우는 `src/jarvis/main.py`에 있으며, 루프 형태로 동작합니다.

1) wakeword 대기
2) greet(TTS)
3) record(고정 길이 녹음)
4) STT
5) intent parse (Local-First)
6) dispatch (unknown이거나 복합 의도일 경우 Mirai_brain으로 Fallback 전달)
7) speak(TTS)

---

## 5-1) 텍스트 명령 인입 경로 (Text Command Ingress)

음성 외에 외부 시스템(예: iOS 단축어)이 **텍스트 명령**을 REST로 전달하는 보조 인입 경로를 둔다.

- 인입 텍스트는 **STT 출력과 동일하게 취급**되어, 위 플로우의 **5) intent parse 단계부터 동일하게** 처리된다.
- 즉 Wakeword/Audio I/O/STT Layer만 건너뛰고, Intent → Router → Domain → **Policy** → Storage는 음성과 같은 코드 경로를 공유한다.
- **Policy Layer(안전/권한/rate-limit)는 텍스트 경로에서도 동일하게 강제**되며 우회할 수 없다.
- 응답은 발화(TTS) 대신 호출자에게 텍스트/구조화 데이터로 반환한다(옵션으로 로컬 발화 가능).
- 계약 상세: `docs/api_contracts/text_command_api.md` (현재 설계 초안, 미구현)

---

## 6) 문서 맵

- 통합 운영 헌법: 최상위 `OPERATING.md`
- Jarvis 운영/안전 규칙: `OPERATING_RULES.md`
- 세션/복구: `RECOVERY_GUIDE.md`
- 검증 단계 기록: `MILESTONES.md`
- 릴리즈 기록: `CHANGELOG.md`
- 앞으로의 방향: `ROADMAP.md`
- 물리/오디오/안전/계약: `docs/`