🌌 미라이 스페이스 프로젝트 운영 헌장 (Mirai Space Project OPERATING.md)
이 문서는 라즈베리 파이 5 기반의 통합 AI 시스템인 '미라이 스페이스 프로젝트(Mirai Space)'의 핵심 운영 원칙과 아키텍처를 정의한다. 모든 서브 시스템(Jarvis, Personal_Service, Home_IoT, Aqua_DCS, Mirai_brain)은 이 헌장의 원칙을 따른다.

🏛️ 핵심 운영 철학
지능의 중앙 집중화 (Centralized Intelligence): 모든 고차원적 논리 판단, 모호한 의도 해석(2차 인텐트 분석), 다단계 작업 계획 수립은 Mirai_brain이 전담한다.
인터페이스의 최소화 (Minimal Interface): 자비스(Jarvis / Pepper)는 시스템의 '입과 귀' 역할에 집중하며, 런타임 경로에서의 자체적인 장시간 논리 처리를 최소화한다.
도메인별 최적화 및 주권 보장 (Domain-Specific Sovereignty):
Personal_Service: 개인화 지능 서비스의 '독립성'과 '재사용성'을 위해 독립적인 외부 도메인 모듈로 유지하며, Mirai_brain이 표준 JSON 계약으로 호출·제어한다.
Home_IoT: '안정성'과 '확장성'을 위해 독립적인 전문 도메인 제어 시스템 및 실행 엔진으로 유지한다.
Aqua_DCS: 전문 분야의 '안정적 독립성' 및 수조 안전(Fail-safe)을 위해 기존 구조를 확고히 유지한다.
환경 격리를 통한 안정성 확보 (Environment Separation): 시스템 운영의 연속성을 위해 개발 환경(dev)과 실제 운영 환경(prod)을 완전히 격리하여 관리한다.

🧠 시스템별 역할 분담
1. Mirai_brain (The Brain / Orchestrator)
역할: 전체 시스템의 중앙 의미 해석 허브 및 최상위 오케스트레이션 계층 (Gemini 2.5 Flash 기반).
핵심 책임:
Jarvis로부터 전달받은 1차 인텐트 및 모호한 자연어의 정밀 분석 및 최종 의도(Intent) 확정.
복합적인 사용자 요청에 대한 단계별 실행 계획(Plan) 수립.
개인화 도메인 서비스(Personal_Service)에 정규화된 JSON 명령 전달 및 응답 데이터 종합.
외부 도메인 시스템(Home_IoT, Aqua_DCS)에 정규화된 JSON 명령 전달 및 응답 데이터 종합.
사용자에게 전달할 최종 발화 멘트의 구조적 확정.
제한 사항: 의미 해석과 계획 수립을 담당하되, 하위 도메인 시스템 고유의 내부 안전 책임 및 최종 실행 정책을 무단 침범하거나 대체하지 않는다.

2. 자비스 (Jarvis / Pepper - The Interface)
역할: 사용자 접점 및 음성 인터페이스 라우터.
핵심 책임:
웨이크워드(Wake Word) 처리 및 로컬 음성 입출력(STT/TTS).
사용자 발화에 대한 로컬 우선(Local-First) 1차 의도 추정 및 신뢰도(Confidence) 산출.
규칙 기반 처리가 불가능한 모호한 요청이나 복합 추론 필요 시 Mirai_brain으로의 핸드오버 및 JSON 페이로드 전달.
Mirai_brain으로부터 받은 최종 응답 멘트 출력.
제한 사항: 직접적인 GPIO 제어, 센서 직접 읽기 등을 수행하지 않으며, 복잡한 외부 제어 로직을 직접 판단하지 않는다.

3. 퍼스널 서비스 (Personal_Service - Integrated Intelligence)
역할: 개인 생활 보조 전문 지능 서비스.
구조: 독립적인 외부 도메인 모듈.
핵심 책임:
시간/날짜 조회, 날씨 정보 브리핑, 알람 및 리마인더 관리 기능 제공.
Mirai_brain의 직접적인 통제 하에 유기적이고 고지능형인 개인 맞춤 서비스 제공.

4. 홈 IoT (Home_IoT - Stable Domain)
역할: 집안 기기 제어 도메인의 전문 시스템이자 실행 엔진.
구조: 독립적인 외부 도메인 모듈.
핵심 책임:
RF, IR, Zigbee, SmartThings 등 다양한 스마트홈 통신 프로토콜 및 MQTT 계층 관리.
하드웨어 제어의 안정성 확보, 명령 큐(Queue) 관리, 예약 작업 스케줄링 및 실패/재시도 처리.
자연어 원문을 직접 해석하지 않으며, Mirai_brain 등으로부터 정규화된 JSON 명령을 수신하여 안전하게 실행 후 상태 반환.

5. 아쿠아 DCS (Aqua_DCS - Specialized Domain)
역할: 해수어항 모니터링 및 제어 전문 시스템.
구조: 독립적인 외부 도메인 모듈.
핵심 책임:
수조 환경 센서 데이터 수집, 이상 탐지 및 실시간 경보 정책 수행.
최상위 AI 계층의 서비스 장애나 네트워크 단절 시에도 수조 생태계 생존을 위한 비본질적 안전 제어 루틴(ESD/Fail-safe)을 완전히 독립적으로 수행.


🔄 데이터 흐름 및 통신 원칙
JSON 기반 표준 계약: Mirai_brain과 각 도메인 시스템(Personal_Service, Home_IoT, Aqua_DCS) 간의 명령 전달, 계획 제안 및 상태 보고는 엄격하게 표준화된 JSON 포맷 계약을 사용한다.
로컬 우선 처리 및 비동기 핸드오버: Jarvis는 저위험 단순 명령 및 고정 질의를 로컬 규칙으로 즉시 라우팅하며, 복잡한 요청은 Mirai_brain으로 넘겨 비동기적으로 응답을 대기하고 연속 대화 세션을 관리한다.
계층적 단일 진입 경로: 모든 고차원 제어 계획 및 종합 질의는 Mirai_brain을 거쳐야 하며, Jarvis가 도메인 시스템의 내부 로직을 직접 호출하거나 하위 도메인 시스템 간에 구조적 합의 없이 직접 통신하는 것을 금지한다.
Home_IoT Canonical Contract: Home_IoT는 하부 통신 세부사항을 추상화하여 가능한 한 하나의 canonical JSON command schema로 요청/응답을 처리한다.
Canonical ID 우선 원칙: 음성 별칭(Alias)은 의미 해석 단계의 보조 수단일 뿐이며, 실제 도메인 실행 계층에서는 언제나 변하지 않는 canonical device id 및 action id를 기준으로 동작한다.
추적성 유지 (Traceability): 모든 요청, 계획, 이벤트는 고유 식별자(request_id, plan_id, trace_id)를 가져야 하며 계층 간 이동 시 상위 요청과의 연결 정보가 완벽히 추적 가능해야 한다.


🛠️ 개발 및 관리 원칙
형상 격리 및 테스트 환경 분리: 모든 코드 작성, 의존성 패키지 설치 및 아키텍처 실험은 검증 전용인 dev 디렉토리 환경에서 수행한다. dev에서 완벽히 안전성이 검증된 코드 정책만 실제 가동 중인 prod 환경으로 이관 배포한다.
도메인 모듈 독립성 (Personal_Service): Personal_Service는 Home_IoT/Aqua_DCS와 마찬가지로 독립적인 외부 도메인 모듈로 관리하며, 자체 디렉토리와 독립 venv를 가진다. Mirai_brain과는 코드 결합 없이 표준 JSON 계약으로만 연동한다.
결과 중심 응답 구분: 모든 내부 통신 및 인터페이스 응답은 사용자에게 출력할 메시지(message)와 시스템 제어용 데이터(data)를 엄격히 분리하여 구조화한다.
실패 원인 및 의도 정정 기록: 모든 실행 실패 및 사용자의 의도 정정 발화는 디버깅 및 향후 로컬 의도 추정 보조 데이터로 활용될 수 있도록 SQLite 등의 감사 로그(Audit trail)에 누락 없이 기록한다.
최종 수정일: 2026-05-25