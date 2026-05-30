# Aqua-DCS Architecture Rules (ARCH_RULES)

이 문서는 **운영 규칙(OPERATING_RULES.md)을 만족하기 위한 설계 규칙**이다.
OPERATING_RULES.md와 충돌할 경우 **OPERATING이 최우선**이다.

---

## 1) 레이어 책임과 금지 규칙

### Drivers (하드웨어 접근)
- GPIO/I2C/sysfs 등 **하드웨어 접근만** 수행
- DB 접근 금지
- Web/Flask import 금지

### Actuators (출력 장치 드라이버)
- MOSFET/릴레이/스마트플러그 등 출력 장치 제어
- **직접 GPIO 구동 금지**, 중간 계층 필수
- DB 접근 금지

### Services (비즈니스 로직)
- 보정/알람/제어/스케줄 등 **로직만** 담당
- 하드웨어 직접 접근 금지 (Drivers/Actuators 통해야 함)

### Storage (데이터 접근)
- 모든 SQL은 storage/ 내부에만 둔다
- 스키마 변경은 migration 또는 명시적 초기화 경로 필요

### Collector (수집 프로세스)
- 주기적 실행, **쓰기 전용**
- Web 노출 금지

### Web (HMI/API)
- **읽기 전용** (제어 요청만 전달)
- 하드웨어 접근 금지
- 무거운 계산/집계는 services로 분리

---

## 2) 제어(Control) 구조
- 제어 명령은 `services/control.py`를 통해서만 실행
- Web은 **명령 요청을 기록**하고 services가 수행
- 제어 로직은 **idempotent** 해야 한다

---

## 3) DCS vs ESD 분리
- DCS는 편의/모니터링/제어 UI 제공
- ESD는 **독립적 Fail-safe 판단/실행**
- ESD는 DCS 의존 금지

---

## 4) 데이터 흐름 규칙
- Collector → Storage (write)
- Web → Storage (read)
- Services ↔ Storage (read/write)
- Drivers/Actuators ↔ Services (직접 데이터 저장 금지)

---

## 5) 시간/단위 규칙
- DB 저장은 UTC 기준
- UI는 KST 변환 표시
- 센서 raw/calibrated 분리 저장

---

## 6) 확장 규칙
- 신규 폴더/모듈은 **목적/책임/의존성** 명시
- 기존 레이어 경계 변경 금지
