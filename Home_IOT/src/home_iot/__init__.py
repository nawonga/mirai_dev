"""Home_IOT — 스마트홈 기기 제어 도메인 실행 엔진.

자연어를 해석하지 않는다. 정규화된 JSON 명령(canonical device id / action id)을
받아 deterministic 하게 실행하고 {ok, message, data}로 반환한다.
(계약: docs/JSON_COMMAND_SCHEMA.md, docs/ALIAS_ACTION_STANDARD.md)
"""

__version__ = "0.0.1"
