# Home_IOT

미라이 스페이스의 **스마트홈 기기 제어 도메인 실행 엔진**.
자연어를 해석하지 않는다. **정규화된 JSON 명령**(canonical device id / action id)을 받아
deterministic 하게 실행하고 `{ok, message, data}`로 반환한다.

> 계약: `docs/JSON_COMMAND_SCHEMA.md`, `docs/ALIAS_ACTION_STANDARD.md`
> 운영 규칙: `OPERATING_RULES.md` (상위: 최상위 `OPERATING.md`)

## 구조
```
src/home_iot/
  engine.py            # ★ handle_json(request) — canonical contract 단일 진입점
  registry.py          # 디바이스 레지스트리(storage/device_registry.json)
  aliases.py           # 음성표현/별칭 → canonical id/action 정규화
  adapters/
    base.py            # Adapter 인터페이스
    mock.py            # MockAdapter (하드웨어 없이 동작·검증)
    broadlink_ir.py    # Broadlink IR 어댑터 (RM4 Pro, 하드웨어 필요 — 미검증)
  main.py              # CLI (내부 transport)
storage/device_registry.json
```

## 연동 모델 (Mirai_brain → Home_IOT)
- 외부 계약의 기준은 **JSON request/response**다. CLI/HTTP는 transport일 뿐.
- 상위(Mirai_brain)는 `engine.handle_json(request)`를 호출하면 된다. (CLI `handle-json`이 stdin 브릿지)
- 지원 operation: `list_devices`, `list_actions`, `execute_action`, `get_status`.
- 요청은 `request_id`/`trace_id`를 보존하여 응답에 반영(추적성).

## CLI 사용 (dev)
```bash
cd /home/nawonga/MiraiProject/dev/Home_IOT
PYTHONPATH=src venv/bin/python -m home_iot.main list-devices
PYTHONPATH=src venv/bin/python -m home_iot.main list-actions --device tv
PYTHONPATH=src venv/bin/python -m home_iot.main control-device --device "거실 불" --action 켜줘
PYTHONPATH=src venv/bin/python -m home_iot.main get-status --device 거실등

# JSON 브릿지 (Mirai_brain이 쓰는 경로)
echo '{"operation":"execute_action","device_id":"티비","action":"음소거","request_id":"req-1"}' \
  | PYTHONPATH=src venv/bin/python -m home_iot.main handle-json
```

## 레지스트리
- `storage/device_registry.json` — controllers(컨트롤러) + devices(canonical id, protocol, aliases, actions).
- 현재 샘플 기기(tv/living_room_light/aircon)는 `protocol: "mock"` 으로, **하드웨어 없이 JSON 계약을 검증**한다.
- 실제 IR 제어로 전환: 해당 device의 `protocol`을 `ir`로 바꾸고 `controller_id`를 broadlink 컨트롤러로 지정,
  각 action에 학습된 IR 코드 경로(`code_path`)를 채운다.

## 어댑터 상태
- **mock**: ✅ 동작/검증 완료 (토글 power, 상태형 power_on/off, get_status persist).
- **broadlink_ir**: ⚠️ 구현됐으나 **하드웨어 미연결로 미검증**. RM4 Pro가 LAN에 있으면 활성화.
  - 과거 확인된 장치: IP `192.168.0.242`, MAC `34:8E:89:2E:20:19`, type `rm4pro`(21003).
  - 탐색: `PYTHONPATH=src venv/bin/python -m home_iot.main discover-rm4`
  - IR 학습/전송은 `adapters/broadlink_ir.py`의 `learn()`/`execute_action()` 참고(추후 CLI 노출 예정).

## 미구현 / 다음
- Broadlink IR 어댑터 하드웨어 검증, IR 학습 CLI(`learn-ir`/`send-ir`).
- Zigbee2MQTT 어댑터(동글 + MQTT 필요), 로컬 스위치 자동화(`docs/zigbee_switch_automation.md`).
- HTTP 노출(FastAPI로 `engine.handle_json` 래핑) — Mirai_brain REST 연동 시.

## 보안
- `.env`의 키/시크릿은 코드 하드코딩·깃 커밋 금지.
