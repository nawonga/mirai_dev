"""디바이스 레지스트리 — canonical id 단일 진실 원천(storage/device_registry.json)."""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]   # .../Home_IOT
REGISTRY_PATH = REPO_ROOT / "storage" / "device_registry.json"


def load_registry(path: str | Path | None = None) -> dict:
    p = Path(path) if path else REGISTRY_PATH
    if not p.is_file():
        return {"controllers": {}, "devices": {}}
    return json.loads(p.read_text(encoding="utf-8"))


def save_registry(reg: dict, path: str | Path | None = None) -> None:
    p = Path(path) if path else REGISTRY_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")


def get_device(reg: dict, device_id: str) -> dict | None:
    return reg.get("devices", {}).get(device_id)


def get_controller(reg: dict, controller_id: str) -> dict | None:
    return reg.get("controllers", {}).get(controller_id)
