"""어댑터 인터페이스."""
from __future__ import annotations


class Adapter:
    """프로토콜 어댑터 베이스. 실행 결과를 dict(delivery/state 등)로 반환한다."""

    name = "base"

    def execute_action(self, device_id: str, device_cfg: dict, action: str) -> dict:
        raise NotImplementedError

    def get_status(self, device_id: str, device_cfg: dict) -> dict:
        return {"state": "unknown"}
