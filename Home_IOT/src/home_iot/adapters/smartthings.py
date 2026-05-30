"""SmartThings 어댑터 — SmartThings Cloud REST API (api.smartthings.com/v1).

인증: Personal Access Token (`.env`의 SMARTTHINGS_TOKEN). 코드 하드코딩 금지.
device_cfg에 `st_device_id`(SmartThings deviceId)가 있어야 한다.

canonical action 매핑(switch capability 기반):
- power_on  → switch/on
- power_off → switch/off
- power     → 현재 상태 읽어 토글
(level 등 인자가 필요한 동작은 추후 JSON contract의 params 확장과 함께 지원)
"""
from __future__ import annotations

import os

from ..env import load_env
from .base import Adapter

BASE = "https://api.smartthings.com/v1"


def _token() -> str:
    load_env()
    t = os.environ.get("SMARTTHINGS_TOKEN")
    if not t:
        raise RuntimeError("SMARTTHINGS_TOKEN(.env)이 없습니다. SmartThings PAT를 설정하세요.")
    return t


class SmartThingsAdapter(Adapter):
    name = "smartthings"

    def __init__(self) -> None:
        self._session = None

    def _sess(self):
        if self._session is None:
            import requests

            s = requests.Session()
            s.headers.update({"Authorization": f"Bearer {_token()}"})
            self._session = s
        return self._session

    # --- 디스커버리/상태 ---
    def list_devices(self) -> list[dict]:
        r = self._sess().get(f"{BASE}/devices", timeout=10)
        r.raise_for_status()
        return r.json().get("items", [])

    def get_status(self, device_id: str, device_cfg: dict) -> dict:
        st_id = device_cfg.get("st_device_id")
        if not st_id:
            raise RuntimeError(f"'{device_id}'에 st_device_id가 없습니다.")
        r = self._sess().get(f"{BASE}/devices/{st_id}/status", timeout=10)
        r.raise_for_status()
        main = r.json().get("components", {}).get("main", {})
        out: dict = {}
        sw = main.get("switch", {}).get("switch", {}).get("value")
        if sw is not None:
            out["state"] = sw
        lvl = main.get("switchLevel", {}).get("level", {}).get("value")
        if lvl is not None:
            out["level"] = lvl
        return out or {"state": "unknown"}

    # --- 실행 ---
    def _command(self, st_id: str, capability: str, command: str, args: list | None = None) -> None:
        body = {"commands": [{"component": "main", "capability": capability,
                              "command": command, "arguments": args or []}]}
        r = self._sess().post(f"{BASE}/devices/{st_id}/commands", json=body, timeout=10)
        r.raise_for_status()

    def execute_action(self, device_id: str, device_cfg: dict, action: str) -> dict:
        st_id = device_cfg.get("st_device_id")
        if not st_id:
            raise RuntimeError(f"'{device_id}'에 st_device_id가 없습니다.")
        if action == "power_on":
            self._command(st_id, "switch", "on")
            state = "on"
        elif action == "power_off":
            self._command(st_id, "switch", "off")
            state = "off"
        elif action == "power":
            cur = self.get_status(device_id, device_cfg).get("state")
            state = "off" if cur == "on" else "on"
            self._command(st_id, "switch", state)
        else:
            raise RuntimeError(f"SmartThings 어댑터가 '{action}'를 아직 지원하지 않습니다.")
        return {"delivery": "cloud", "provider": "smartthings", "state": state}
