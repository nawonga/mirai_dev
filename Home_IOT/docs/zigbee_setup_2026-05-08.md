# Zigbee2MQTT setup log — 2026-05-08

## Goal
Set up a Sonoff Zigbee 3.0 USB Dongle Plus on the Raspberry Pi and connect the first Zigbee light through Zigbee2MQTT.

## Hardware detection
Host confirmed the dongle correctly:

- USB device: `Sonoff Zigbee 3.0 USB Dongle Plus`
- Driver: `cp210x`
- Device node: `/dev/ttyUSB0`
- Stable serial path:
  - `/dev/serial/by-id/usb-ITead_Sonoff_Zigbee_3.0_USB_Dongle_Plus_1a5bbd66cca3ef118cd74cbd61ce3355-if00-port0`

## Home_IOT changes
Updated `.env`:

```env
ZIGBEE_PORT=/dev/serial/by-id/usb-ITead_Sonoff_Zigbee_3.0_USB_Dongle_Plus_1a5bbd66cca3ef118cd74cbd61ce3355-if00-port0
```

Added Docker-based Zigbee stack in `Home_IOT`:

- `docker-compose.yml`
- `zigbee/mosquitto/config/mosquitto.conf`
- `zigbee/zigbee2mqtt/data/configuration.yaml`
- `zigbee/README.md`

## Stack design
Services:

- `mosquitto`
- `zigbee2mqtt`

Ports:

- MQTT: `1883`
- Zigbee2MQTT frontend: `8080`

Important Zigbee2MQTT serial config:

```yaml
serial:
  port: /dev/zigbee
  adapter: zstack
```

The compose file maps the host serial device from `${ZIGBEE_PORT}` to `/dev/zigbee` inside the container.

## Troubleshooting done
### Initial failure
Zigbee2MQTT first failed with:

- `USB adapter discovery error (No valid USB adapter found)`

### Fixes applied
1. Switched from raw tty assumption to stable by-id serial path in `.env`
2. Added explicit Zigbee adapter type:
   - `adapter: zstack`
3. Recreated containers with:

```bash
docker compose down
docker compose up -d
```

4. Verified container device mapping:

```bash
docker exec -it homeiot-zigbee2mqtt sh -lc 'ls -l /dev/zigbee'
```

Result:
- `/dev/zigbee` exists inside the container
- Zigbee2MQTT frontend became reachable on port `8080`

## Pairing result
A Zigbee light was put into pairing mode.

Then:
- `permit_join` was enabled in the Zigbee2MQTT web UI
- the device joined successfully
- the device appeared in the UI
- all controls worked normally

## Current status
Confirmed working:

- Sonoff Zigbee dongle recognized by host
- Mosquitto running
- Zigbee2MQTT running
- Web UI reachable
- First Zigbee light paired and controllable

## Suggested next steps
- Turn `permit_join` back off after pairing sessions
- Rename devices with stable friendly names
- Decide how Home_IOT will consume/control MQTT device state
- Add more Zigbee devices incrementally
