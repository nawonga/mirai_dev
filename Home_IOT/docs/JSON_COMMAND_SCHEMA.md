# Home_IOT JSON Command Schema

Home_IOT는 OpenClaw로부터 구조화된 JSON 요청을 받아 실행하는 것을 canonical contract로 삼는다.
현재 bridge -> Home_IOT 경로는 `python3 -m home_iot.main handle-json` stdin JSON 방식으로 연결된다.

## Design goals
- RF/IR/Zigbee/SmartThings를 하나의 요청/응답 형식으로 통일
- OpenClaw가 최종 호출 판단을 담당하고, Home_IOT는 도메인 실행을 담당
- fire-and-forget 제어와 상태 조회(get_status)를 같은 계약 안에서 다룸
- request_id / trace_id / source / requester / zone 같은 메타데이터를 확장 가능하게 유지

## Request envelope (recommended)

```json
{
  "domain": "home_iot",
  "operation": "execute_action",
  "device_id": "tv",
  "action": "power",
  "request_id": "req-001",
  "trace_id": "trace-001",
  "source": "openclaw",
  "request_source": "openclaw_bridge",
  "requester": "jimi",
  "context": {
    "zone": "living_room",
    "input_mode": "voice"
  }
}
```

## Common request fields
- `domain`: always `home_iot`
- `operation`: what Home_IOT should do
- `device_id`: registry device id
- `action`: button/action name for control operations
- `request_id`: caller request id (optional but recommended)
- `trace_id`: end-to-end trace id (optional but recommended)
- `source`: logical caller (`openclaw`, `jarvis`, `test`)
- `request_source`: bridge/runtime source detail
- `requester`: human or system requester
- `context`: zone/node/input metadata

## Supported operations (current / planned)

### 1. `execute_action`
For IR/RF/Zigbee/SmartThings action execution.

Example:
```json
{
  "domain": "home_iot",
  "operation": "execute_action",
  "device_id": "tv",
  "action": "power"
}
```

Expected semantics:
- IR/RF: usually fire-and-forget
- Zigbee/SmartThings: may return post-action state when available

### 2. `get_status`
For device status/state query.

Example:
```json
{
  "domain": "home_iot",
  "operation": "get_status",
  "device_id": "aircon"
}
```

Expected semantics:
- returns current known state or live adapter result
- should include protocol-specific state fields when available

### 3. Planned future operations
- `learn_action`
- `register_device`
- `promote_action`
- `rollback_action`
- `list_devices`
- `list_actions`

## Response schema

```json
{
  "ok": true,
  "message": "'tv' 기기의 'power' 동작을 실행했어요.",
  "data": {
    "operation": "execute_action",
    "device": "tv",
    "action": "power",
    "protocol": "ir",
    "controller_id": "broadlink_rm4_pro_1",
    "delivery": "fire_and_forget"
  }
}
```

## Common response fields
- `ok`: boolean
- `message`: user-facing summary text
- `data`: structured system payload

## Recommended response data fields
- `operation`
- `device`
- `action`
- `protocol`
- `controller_id`
- `delivery` (`fire_and_forget` / `stateful`)
- `request_id`
- `trace_id`
- `registry_path` (when relevant)
- `status` / protocol-specific state values

## Alias / action mapping standard
Home_IOT should separate:
1. **device registry ids** (stable canonical ids)
2. **spoken aliases / synonyms** (NLU-facing)
3. **runtime actions** (stable canonical action ids)

### Canonical device ids
- `tv`
- `aircon`
- `fan`
- `living_room_light`
- `bedroom_light`

### Canonical action ids
- `power`
- `power_on`
- `power_off`
- `volume_up`
- `volume_down`
- `mute`
- `input`
- `temp_up`
- `temp_down`
- `mode_cool`
- `mode_dry`
- `speed_up`
- `speed_down`
- `oscillation`

### Alias mapping example
```json
{
  "devices": {
    "tv": ["tv", "티비", "텔레비전"]
  },
  "actions": {
    "power": ["켜", "꺼", "전원", "켜줘", "꺼줘"],
    "volume_up": ["볼륨 올려", "소리 키워"],
    "volume_down": ["볼륨 내려", "소리 줄여"]
  }
}
```

## Important rule
- Alias parsing is not the final authority.
- Jarvis may do first-pass classification.
- OpenClaw decides whether Home_IOT should be called.
- Home_IOT executes canonical device/action requests based on registry and adapter capability.
