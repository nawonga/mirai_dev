# OPERATING.md
# Mirai Space Constitution
## 미라이 스페이스 운영 헌법

이 문서는 **미라이 스페이스(Mirai Space)** 전체의 최상위 운영 원칙이다.
Jarvis, Aqua-DCS, Mirai_brain, Home_IOT는 이 문서의 규칙을 따른다.

이 문서는 각 프로젝트의 세부 운영 문서보다 우선한다.
다만, 각 프로젝트의 **도메인 고유 안전 규칙**은 그 프로젝트의 전문 책임 범위 안에서 강하게 존중된다.

---

## Document Status
- **Document Name:** Mirai Space Constitution
- **System Name:** 미라이 스페이스 (Mirai Space)
- **Current Version:** v0.5
- **Status:** Draft
- **Last Revised:** 2026-05-25 KST

---

## Naming Principle
### System Name
- **미라이 스페이스 (Mirai Space)** 는 시스템 전체 이름이다.

### Project Names
- **Jarvis**: 음성 인터페이스 및 1차 라우터
- **Aqua-DCS**: 해수어항 제어 및 모니터링 시스템
- **Mirai_brain**: Gemini 2.5 Flash 기반 중앙 의미 해석 허브
- **Home_IOT**: 스마트홈 기기 제어 시스템

### Interaction Identities
- **Pepper**: Jarvis 프로젝트에서 사용자와 상호작용하는 음성 비서의 이름이다.
- 명칭 규칙: 시스템 전체를 지칭할 때는 반드시 **미라이 스페이스**를 사용하며, 사용자와의 대화 인터페이스는 **Pepper**로 칭한다.

---

## 1. 목적
1. 사용자의 의도를 안전하고 정확하게 이해한다.
2. 음성 입력, 의미 해석, 상태 조회, 장치 실행을 계층적으로 처리한다.
3. 실제 기기 제어에서는 항상 안정성, 예측 가능성, 회복 가능성을 우선한다.
4. 편의 기능이 안전 기능을 침범하지 않도록 한다.
5. 개발(Dev)과 운영(Prod) 환경을 격리하여 무중단 및 안전한 업데이트를 보장한다.

---

## 2. 최상위 역할 정의

### 2.1 Jarvis (Pepper)
Jarvis는 기본적으로 미라이 스페이스의 “귀와 입”이다.
- **역할:** wake word 처리, STT/TTS, 사용자 요청 수집, 1차 의도 추정(Local-First), Mirai_brain 및 도메인 시스템과의 입출력 게이트웨이.
- **금지:** 직접적인 GPIO 제어, 런타임 경로에서 장시간 블로킹 AI 호출 대기, 도메인 안전 로직 대체 불가.

### 2.2 Mirai_brain
Mirai_brain은 시스템의 상위 오케스트레이션 및 의미 해석 계층이다. (Gemini 2.5 Flash 기반)
- **역할:** Jarvis가 전달한 STT 최종 해석, 모호한 의도 판단, 복합 실행 계획 수립, 프로젝트 간 정보 종합 후 JSON 형태의 구조화된 의도(intent) 반환.
- **한계:** 실행 계획 수립은 어디까지나 '제안/요청'이며, 도메인 시스템의 내부 안전 책임과 최종 실행 책임을 대체하지 않는다.

### 2.3 Home_IOT
집안 기기 제어 도메인의 전문 시스템이자 실행 엔진.
- **역할:** 장치 추상화, 상태 수집, 명령 실행 큐 관리, 스케줄링. 자연어를 이해하지 않으며 정규화된 명령만 실행한다.

### 2.4 Aqua-DCS
수조 모니터링 및 제어 도메인의 전문 시스템.
- **역할:** 센서 데이터 수집, 이상 탐지, 경보 발생, 수조 도메인 내부 제어 정책 수행.

---

## 3. Domain Sovereignty Principle (도메인 주권 원칙)
각 도메인 시스템은 자신의 전문 책임 영역에 대해 주권을 가진다.
1. 어떤 프로젝트도 다른 프로젝트의 전문 내부 책임을 무단 침범하지 않는다.
2. Mirai_brain은 도메인 시스템에 요청, 조회, 계획 제안은 할 수 있으나, 도메인 안전 정책을 무시할 수 없다.

---

## 4. Safety and Convenience Separation Principle (안전/편의 분리 원칙)
안전 기능과 편의 기능은 철저히 분리된다.
- Aqua-DCS의 ESD(긴급 셧다운)/Fail-safe 경로는 Mirai_brain이나 Jarvis가 다운되더라도 독립적으로 유지되어야 한다.

---

## 5. Environment Separation Principle (개발/운영 격리 원칙)
미라이 스페이스의 안정성을 보장하기 위해 개발(Dev)과 운영(Prod) 환경을 철저히 분리한다.
1. **경로 및 실행 격리:** Dev와 Prod는 별도의 디렉토리와 독립된 가상환경(venv)을 가진다.
2. **테스트 우선:** 모든 새로운 코드, 패키지 설치, 아키텍처 변경은 Dev 환경에서 먼저 검증되어야 한다.
3. **배포 규칙:** Dev에서 정상 동작이 확인되지 않은 코드는 Prod로 이관될 수 없다. Prod 환경은 항상 실행 가능한 안정된 상태를 유지해야 한다.
4. **프로젝트별 venv 격리:** 각 도메인 프로젝트(Jarvis, Mirai_brain, Aqua-DCS, Home_IOT, Personal_Service)는 자신의 디렉토리 내부에 독립된 venv를 가진다. 도메인 주권 원칙에 따라 의존성을 도메인 단위로 격리하며, 여러 프로젝트가 공유하는 단일 통합 venv를 런타임 환경으로 사용하지 않는다. (린터/포매터 등 공용 개발 툴링 전용 venv는 예외적으로 허용될 수 있다.)
   - venv 디렉토리 이름은 `venv`로 통일한다. (Dev/Prod 양쪽 동일)
5. **Dev 단일 원천 원칙 (Single Source of Truth):** 코드뿐 아니라 문서를 포함한 **모든 작업은 Dev에서 수행한다.** 본 헌법(`OPERATING.md`)을 비롯한 모든 운영 문서의 정본은 `dev/` 트리에 두며, 별도의 상위/루트 사본을 두지 않는다. 운영이 가능한 시점에 검증된 운영 버전만 Prod로 이관한다.

---

## 6. Local-First Intent Resolution Principle
Jarvis는 사용자 요청에 대해 항상 **로컬 우선(local-first)** 으로 의도를 추정한다.
- 날짜, 날씨, 단순 상태 조회 등 단순 명령은 Mirai_brain(Gemini)을 호출하지 않고 로컬 규칙으로 즉시 처리한다.
- Mirai_brain 호출은 **모호성 해소 또는 복합 추론이 필요한 경우**에 한정한다.

---

*(이하 기존 10. 예약 및 스케줄링 원칙 ~ 19. 로그와 기록 원칙 동일 유지)*

---

## 20. Revision Policy
- 모든 개정은 시점을 기록하고 무엇이 바뀌었는지 요약한다.
- **2026-05-25 KST — v0.5**
  - Personal_Service를 독립적인 외부 도메인 모듈로 확정 (Mirai_brain ↔ Personal_Service 표준 JSON 계약 연동, 모노레포/내부 흡수 방식 폐기)
  - 프로젝트별 venv 격리 원칙을 환경 분리 원칙(§5)에 신설하고, 통합 단일 venv 런타임 사용을 금지
  - Dev 단일 원천 원칙(§5) 신설 — 문서 포함 모든 작업을 Dev에서 수행하고 정본을 `dev/` 트리에 둔다. 루트 `OPERATING.md` 사본 폐지(정본은 `dev/OPERATING.md`).
- **2026-05-25 KST — v0.4**
  - OpenClaw를 Mirai_brain(Gemini 2.5 Flash) 아키텍처로 전면 대체
  - Dev/Prod 환경 분리 원칙(Environment Separation Principle) 신설