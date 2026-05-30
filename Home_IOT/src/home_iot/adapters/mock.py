"""Mock 어댑터 — 하드웨어 없이 JSON 계약을 end-to-end 검증하기 위한 가짜 실행기.

프로세스 메모리에 토글 상태를 흉내내어 get_status가 동작하도록 한다.
"""
from __future__ import annotations

from .base import Adapter


class MockAdapter(Adapter):
    name = "mock"

    def __init__(self) -> None:
        self._state: dict[str, str] = {}

    def execute_action(self, device_id: str, device_cfg: dict, action: str) -> dict:
        if action == "power_on":
            self._state[device_id] = "on"
        elif action == "power_off":
            self._state[device_id] = "off"
        elif action == "power":
            self._state[device_id] = "off" if self._state.get(device_id) == "on" else "on"
        # 그 외(volume 등)는 상태 변화 없이 fire-and-forget로 간주
        return {"delivery": "mock", "state": self._state.get(device_id, "unknown")}

    def get_status(self, device_id: str, device_cfg: dict) -> dict:
        return {"state": self._state.get(device_id, "unknown")}
