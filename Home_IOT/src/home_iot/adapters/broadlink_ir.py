"""Broadlink IR 어댑터 (RM4 Pro 등).

⚠️ 하드웨어 필요 — 현재 LAN에 장치가 없어 미검증. 컨트롤러가 연결되면 활성화된다.
IR 코드는 레지스트리 action의 `code_path`(raw bytes 파일)에서 로드해 send_data로 전송한다.
컨트롤러 정보(host/mac/devtype)는 레지스트리 controllers[*]에서 온다.
"""
from __future__ import annotations

import time
from pathlib import Path

from .base import Adapter


class BroadlinkIRAdapter(Adapter):
    name = "ir"

    def __init__(self, controller_cfg: dict) -> None:
        self.cfg = controller_cfg
        self._dev = None

    def _connect(self):
        if self._dev is not None:
            return self._dev
        import broadlink

        host = self.cfg.get("host")
        mac_str = self.cfg.get("mac", "")
        devtype = int(self.cfg.get("devtype", 0x520B))  # rm4 pro 기본값(문서: 21003)
        if not host or not mac_str:
            raise RuntimeError("controller에 host/mac이 없습니다.")
        mac = bytes.fromhex(mac_str.replace(":", ""))
        dev = broadlink.gendevice(devtype, (host, 80), mac)
        dev.auth()
        self._dev = dev
        return dev

    def execute_action(self, device_id: str, device_cfg: dict, action: str) -> dict:
        action_cfg = device_cfg.get("actions", {}).get(action, {})
        code_path = action_cfg.get("code_path")
        if not code_path:
            raise RuntimeError(f"'{device_id}'의 '{action}'에 IR code_path가 없습니다(미학습).")
        p = Path(code_path)
        if not p.is_absolute():
            # 레지스트리 상대경로는 Home_IOT 루트 기준
            p = Path(__file__).resolve().parents[3] / code_path
        data = p.read_bytes()
        self._connect().send_data(data)
        return {"delivery": "fire_and_forget", "controller": self.cfg.get("id")}

    def learn(self, timeout: float = 10.0) -> bytes:
        """학습 모드 진입 후 IR 코드 1개 캡처. (CLI learn-ir에서 사용)"""
        dev = self._connect()
        dev.enter_learning()
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(0.5)
            try:
                data = dev.check_data()
                if data:
                    return data
            except Exception:
                continue
        raise TimeoutError("IR 코드를 캡처하지 못했습니다(시간 초과).")
