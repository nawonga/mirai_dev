# Zigbee switch automation

## Goal
Handle local Zigbee switch events without routing through Jarvis/OpenClaw intent flow.

Primary voice/control flow remains:
- Jarvis -> OpenClaw -> Home_IOT -> Zigbee2MQTT

Local switch automation flow is separate:
- Zigbee2MQTT event -> Home_IOT automation runner -> Zigbee2MQTT command

## Current rule
- Source device: `Skyblue_switch`
- Trigger: `action == "single"`
- Target device: `test_light`
- Action: publish `{ "state": "TOGGLE" }` to `zigbee2mqtt/test_light/set`

## Files
- Rules: `config/automation_rules.json`
- Runner: `src/home_iot/automation.py`

## Example run
```bash
cd /home/nawonga/Projects/Home_IOT
PYTHONPATH=src python3 -m home_iot.main run-automation
```

## Design notes
- Keeps event automation separate from canonical Home_IOT request/response path.
- Avoids coupling switch latency to Jarvis/OpenClaw availability.
- Uses deterministic rule matching only.
