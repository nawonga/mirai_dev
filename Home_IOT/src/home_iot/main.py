"""Home_IOT CLI — 내부 transport. 외부 계약의 기준은 JSON request/response(engine.handle_json).

예:
    PYTHONPATH=src python -m home_iot.main list-devices
    PYTHONPATH=src python -m home_iot.main control-device --device tv --action 켜줘
    PYTHONPATH=src python -m home_iot.main get-status --device tv
    echo '{"operation":"execute_action","device_id":"tv","action":"power"}' \
        | PYTHONPATH=src python -m home_iot.main handle-json
"""
from __future__ import annotations

import argparse
import json
import sys

from . import engine, registry


def _print(resp: dict) -> int:
    print(json.dumps(resp, ensure_ascii=False, indent=2))
    return 0 if resp.get("ok") else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Home_IOT CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list-devices", help="등록된 기기 목록")

    p = sub.add_parser("list-actions", help="기기의 지원 동작")
    p.add_argument("--device", required=True)

    p = sub.add_parser("control-device", help="기기 동작 실행")
    p.add_argument("--device", required=True)
    p.add_argument("--action", required=True)

    p = sub.add_parser("get-status", help="기기 상태 조회")
    p.add_argument("--device", required=True)

    sub.add_parser("handle-json", help="stdin JSON 명령 처리")
    sub.add_parser("discover-rm4", help="LAN Broadlink 장치 탐색(하드웨어)")

    sub.add_parser("st-list-devices", help="SmartThings 기기 목록(토큰 필요)")
    p = sub.add_parser("st-register", help="SmartThings 기기를 레지스트리에 등록")
    p.add_argument("--st-id", required=True, help="SmartThings deviceId")
    p.add_argument("--id", required=True, dest="canonical", help="등록할 canonical device id")
    p.add_argument("--display", help="표시 이름(기본: ST label)")
    p.add_argument("--zone", default="", help="구역")

    args = ap.parse_args(argv)

    if args.cmd == "list-devices":
        return _print(engine.handle_json({"operation": "list_devices"}))
    if args.cmd == "list-actions":
        return _print(engine.handle_json({"operation": "list_actions", "device_id": args.device}))
    if args.cmd == "control-device":
        return _print(engine.handle_json(
            {"operation": "execute_action", "device_id": args.device, "action": args.action}))
    if args.cmd == "get-status":
        return _print(engine.handle_json({"operation": "get_status", "device_id": args.device}))
    if args.cmd == "handle-json":
        try:
            req = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            return _print({"ok": False, "message": "JSON 파싱 실패", "data": {"error": str(e)}})
        return _print(engine.handle_json(req))
    if args.cmd == "discover-rm4":
        import broadlink
        devs = broadlink.discover(timeout=5)
        print(json.dumps(
            [{"devtype": d.devtype, "host": d.host[0],
              "mac": ":".join("%02x" % b for b in d.mac[::-1])} for d in devs],
            ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "st-list-devices":
        from .adapters.smartthings import SmartThingsAdapter
        try:
            devs = SmartThingsAdapter().list_devices()
        except Exception as e:
            print(f"SmartThings 조회 실패: {type(e).__name__}: {e}")
            print("→ .env의 SMARTTHINGS_TOKEN 확인 (만료/오타/스코프 부족). "
                  "새로 만든 PAT는 24시간 만료 정책 주의 — 재발급 후 즉시 시도.")
            return 1
        for d in devs:
            caps = sorted({c["id"] for comp in d.get("components", [])
                           for c in comp.get("capabilities", [])})
            print(f"{d.get('deviceId')}  | {d.get('label') or d.get('name')}  | caps: {', '.join(caps)}")
        print(f"\n총 {len(devs)}개")
        return 0
    if args.cmd == "st-register":
        from .adapters.smartthings import SmartThingsAdapter
        try:
            devs = SmartThingsAdapter().list_devices()
        except Exception as e:
            print(f"SmartThings 조회 실패: {type(e).__name__}: {e}")
            return 1
        match = next((d for d in devs if d.get("deviceId") == args.st_id), None)
        if not match:
            print(f"deviceId '{args.st_id}' 를 SmartThings에서 찾지 못했습니다.")
            return 1
        caps = {c["id"] for comp in match.get("components", [])
                for c in comp.get("capabilities", [])}
        actions: dict = {}
        if "switch" in caps:
            actions.update({"power": {}, "power_on": {}, "power_off": {}})
        reg = registry.load_registry()
        reg.setdefault("controllers", {}).setdefault("smartthings_cloud", {"type": "smartthings"})
        reg.setdefault("devices", {})[args.canonical] = {
            "display_name": args.display or match.get("label") or match.get("name"),
            "protocol": "smartthings",
            "controller_id": "smartthings_cloud",
            "zone": args.zone,
            "st_device_id": args.st_id,
            "aliases": [],
            "actions": actions,
        }
        registry.save_registry(reg)
        print(f"등록됨: {args.canonical} (capabilities: {sorted(caps)})")
        print(json.dumps(reg["devices"][args.canonical], ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
