# Home_IOT Operating Rules

이 문서는 Home_IOT 프로젝트의 운영 규칙을 정의한다.
상위 `/home/node/.openclaw/workspace/OPERATING.md` 의 원칙을 Home_IOT 도메인에 구체 적용한다.

## 1) 역할 정의
- Home_IOT는 RF/IR/Zigbee/SmartThings 등 집안 기기 제어를 담당하는 독립 도메인 시스템이다.
- Home_IOT는 자체적으로 고차원 판단을 하지 않는다.
- 최종 호출 여부, 실행 우선순위, 복합 작업 계획은 OpenClaw가 판단한다.
- Jarvis는 Home_IOT의 직접 제어 주체가 아니라, OpenClaw로 요청을 넘기는 인터페이스다.

## 2) 단일 진입 원칙
- 음성 경로 기준 외부 제어 요청은 반드시 OpenClaw를 거쳐야 한다.
- Home_IOT는 OpenClaw가 만든 구조화된 요청(JSON/CLI/API 계약)을 실행하고 결과를 반환한다.
- Jarvis가 Home_IOT의 비즈니스 로직을 직접 소유하거나 개별 장치 코드를 직접 관리하지 않는다.

## 3) 안정성 원칙
- 새 기기 학습/등록은 기존 운영 코드를 직접 덮어쓰지 않는다.
- 활성(active) 코드와 신규 학습(raw/staging) 코드를 분리한다.
- 검증 후 승격(promote), 문제 시 롤백(rollback) 가능해야 한다.
- 한 기기 등록 실패가 다른 기기 제어에 영향을 주지 않도록 기기/버튼/프로토콜 단위를 분리한다.

## 4) Registry 원칙
- Home_IOT는 device registry를 단일 진실 원천으로 사용한다.
- alias / canonical action / JSON contract 관련 변경 전에는 아래 문서를 먼저 확인한다:
  - `/home/node/.openclaw/workspace/Home_IOT/docs/ALIAS_ACTION_STANDARD.md`
  - `/home/node/.openclaw/workspace/Home_IOT/docs/JSON_COMMAND_SCHEMA.md`
- registry는 최소한 다음을 관리해야 한다:
  - device_id
  - display_name
  - protocol(ir/rf/zigbee/smartthings)
  - controller_id
  - room/zone
  - supported actions/buttons
  - active code path
  - history/raw entries
- 런타임은 registry에 등록된 active 항목만 사용한다.
- alias(별칭)와 실제 실행 id는 분리한다.
- registry 및 실행 경로는 canonical device id / action id 기준으로 유지한다.

## 5) OpenClaw 연동 원칙
- OpenClaw는 Home_IOT에 대해 deterministic bridge 또는 명시적 인터페이스로 명령을 전달한다.
- OpenClaw가 Home_IOT에 보내는 canonical contract는 JSON request/response 이다.
- 내부 실행 편의를 위해 CLI가 존재할 수 있으나, 이는 내부 transport일 뿐 외부 계약의 기준이 아니다.
- Home_IOT는 사용자 멘트와 시스템 데이터(data)를 구분해서 반환한다.
- Home_IOT 응답은 최소한 다음을 포함하는 것이 바람직하다:
  - ok
  - message
  - data
  - device
  - action
  - controller
  - trace_id/request_id (가능 시)
- 상태 기반 프로토콜(Zigbee, SmartThings)은 `get_status` 와 같은 JSON operation으로 상태를 반환할 수 있어야 한다.

## 6) 경로 규칙
- 호스트 원본 경로:
  - `/home/nawonga/Projects/Home_IOT`
- OpenClaw 내부 마운트 경로:
  - `/home/node/work/Home_IOT`
- 컨테이너 내부 작업은 `/home/node/work/Home_IOT` 기준으로 수행한다.
- 경로 혼선이 있으면 기능 변경보다 먼저 마운트/실행 경로 정합성을 확인한다.
