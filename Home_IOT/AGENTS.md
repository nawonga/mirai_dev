# AGENTS.md - Home_IOT Router

Home_IOT 작업 전에는 이 문서를 먼저 읽고, 이어서 `OPERATING_RULES.md` 를 읽는다.

상세 규칙:
- `/home/node/.openclaw/workspace/Home_IOT/OPERATING_RULES.md`

## 1) 프로젝트 역할
Home_IOT는 집안 기기 제어를 담당하는 독립 도메인 시스템이다.
RF/IR/Zigbee/SmartThings 등 장치 제어는 여기서 담당한다.
최종 호출 판단과 복합 계획은 OpenClaw가 담당한다.

## 2) canonical 경로
- OpenClaw 작업 경로:
  - `/home/node/.openclaw/workspace/Home_IOT`
- host authoritative 원본:
  - `/home/nawonga/Projects/Home_IOT`

## 3) 이 프로젝트에서 AI가 특히 기억할 것
- Jarvis는 Home_IOT의 직접 실행 주체가 아니라 상위 계층으로 요청을 넘기는 인터페이스다.
- 음성 경로 기준 최종 실행 계획은 OpenClaw가 담당한다.
- Home_IOT는 구조화된 요청(JSON/CLI/API 계약)을 받아 deterministic 하게 실행하고 결과를 반환한다.
- TV 제어 문제는 STT 성공 여부보다 intent 라우팅/Jarvis→OpenClaw→Home_IOT 계약 정합성을 먼저 의심한다.

## 4) 작업 원칙
- device registry를 단일 진실 원천으로 유지한다.
- alias와 실제 실행 id를 분리한다.
- 활성 코드와 학습/실험 코드를 섞지 않는다.
- 한 기기 등록 실패가 다른 기기 제어에 영향을 주지 않게 분리한다.

### alias / action 작업 시 우선 참고 문서
alias, canonical action, JSON contract 관련 작업을 할 때는 아래 문서를 먼저 확인한다.
- `/home/node/.openclaw/workspace/Home_IOT/docs/ALIAS_ACTION_STANDARD.md`
- `/home/node/.openclaw/workspace/Home_IOT/docs/JSON_COMMAND_SCHEMA.md`

특히 다음 작업에서 우선 참고 대상이다:
- spoken alias / synonym 추가 또는 정리
- canonical device id / canonical action id 설계 변경
- Jarvis → OpenClaw → Home_IOT 명령 계약 변경
- registry 구조에 alias 관련 필드 추가
- 새 프로토콜 adapter의 action naming 정리

## 5) 하지 말 것
- Jarvis 쪽에서 Home_IOT 내부 장치 로직을 직접 박아 넣지 말 것
- 기기 추가를 운영 코드 덮어쓰기 방식으로 하지 말 것
- 외부 계약(JSON request/response)보다 ad-hoc 호출을 기준으로 구조를 굳히지 말 것
