"""JSON 명령 엔진 — canonical contract의 단일 진입점.

handle_json(request) → response. CLI(stdin)든 HTTP든 이 함수를 호출하면 된다.
(계약: docs/JSON_COMMAND_SCHEMA.md)
"""
from __future__ import annotations

from . import aliases, registry
from .adapters.base import Adapter
from .adapters.mock import MockAdapter

_adapter_cache: dict[str, Adapter] = {}


def get_adapter(device_cfg: dict, reg: dict) -> Adapter:
    """device protocol/controller에 맞는 어댑터를 반환(컨트롤러 단위 캐시)."""
    protocol = device_cfg.get("protocol", "mock")
    controller_id = device_cfg.get("controller_id", f"_{protocol}")
    if controller_id in _adapter_cache:
        return _adapter_cache[controller_id]

    if protocol == "mock":
        adapter: Adapter = MockAdapter()
    elif protocol in ("ir", "broadlink"):
        from .adapters.broadlink_ir import BroadlinkIRAdapter

        ctrl = registry.get_controller(reg, controller_id) or {}
        ctrl = {**ctrl, "id": controller_id}
        adapter = BroadlinkIRAdapter(ctrl)
    elif protocol == "smartthings":
        from .adapters.smartthings import SmartThingsAdapter

        adapter = SmartThingsAdapter()
    else:
        raise ValueError(f"지원하지 않는 protocol: {protocol}")

    _adapter_cache[controller_id] = adapter
    return adapter


def _resp(ok: bool, message: str, data: dict, req: dict) -> dict:
    return {
        "ok": ok,
        "message": message,
        "data": {
            **data,
            "request_id": req.get("request_id"),
            "trace_id": req.get("trace_id"),
        },
    }


def handle_json(request: dict, reg: dict | None = None) -> dict:
    """정규화된 JSON 명령을 처리한다."""
    reg = reg if reg is not None else registry.load_registry()
    op = request.get("operation")

    if op == "list_devices":
        devices = {
            did: {"display_name": c.get("display_name"), "protocol": c.get("protocol"),
                  "zone": c.get("zone"), "actions": list(c.get("actions", {}).keys())}
            for did, c in reg.get("devices", {}).items()
        }
        return _resp(True, f"{len(devices)}개 기기가 등록되어 있어요.",
                     {"operation": op, "devices": devices}, request)

    # device_id가 필요한 operation들
    device_token = request.get("device_id")
    did = aliases.resolve_device(device_token, reg) if device_token else None
    if op in ("execute_action", "get_status", "list_actions"):
        if not did:
            return _resp(False, f"'{device_token}' 기기를 찾지 못했어요.",
                         {"operation": op, "device": device_token}, request)
        dev = reg["devices"][did]

        if op == "list_actions":
            return _resp(True, f"'{dev.get('display_name', did)}'의 동작 목록이에요.",
                         {"operation": op, "device": did,
                          "actions": list(dev.get("actions", {}).keys())}, request)

        if op == "get_status":
            adapter = get_adapter(dev, reg)
            try:
                status = adapter.get_status(did, dev)
            except Exception as e:
                return _resp(False, "상태를 가져오지 못했어요.",
                             {"operation": op, "device": did, "error": f"{type(e).__name__}: {e}"},
                             request)
            return _resp(True, f"'{dev.get('display_name', did)}' 상태예요.",
                         {"operation": op, "device": did, "protocol": dev.get("protocol"),
                          **status}, request)

        # execute_action
        action_token = request.get("action")
        action = aliases.resolve_action(action_token, set(dev.get("actions", {}))) if action_token else None
        if not action:
            return _resp(False, f"'{dev.get('display_name', did)}'에서 '{action_token}' 동작을 지원하지 않아요.",
                         {"operation": op, "device": did, "requested_action": action_token,
                          "supported": list(dev.get("actions", {}).keys())}, request)
        adapter = get_adapter(dev, reg)
        try:
            result = adapter.execute_action(did, dev, action)
        except Exception as e:
            return _resp(False, f"'{dev.get('display_name', did)}' 제어에 실패했어요.",
                         {"operation": op, "device": did, "action": action,
                          "error": f"{type(e).__name__}: {e}"}, request)
        return _resp(True, f"'{dev.get('display_name', did)}'의 '{action}' 동작을 실행했어요.",
                     {"operation": op, "device": did, "action": action,
                      "protocol": dev.get("protocol"), "controller_id": dev.get("controller_id"),
                      **result}, request)

    return _resp(False, f"알 수 없는 operation: {op}", {"operation": op}, request)
