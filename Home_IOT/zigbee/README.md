# Home_IOT — Zigbee 스택 (Docker)

Mosquitto(MQTT) + Zigbee2MQTT를 Docker로 운영한다. 설계 근거: `../docs/zigbee_setup_2026-05-08.md`.

## 구성
- `../docker-compose.yml` — mosquitto + zigbee2mqtt 서비스
- `mosquitto/config/mosquitto.conf` — MQTT 브로커 설정 (1883)
- `zigbee2mqtt/data/configuration.yaml` — Z2M 설정 (frontend 8080)
- `../.env` — `ZIGBEE_PORT`(동글 by-id 경로) ※ gitignore

## 하드웨어
- Sonoff Zigbee 3.0 USB Dongle Plus (**ZBDongle-P / TI CC2652P**), CP210x → `/dev/ttyUSB0`
- 안정 경로: `/dev/serial/by-id/usb-ITead_Sonoff_Zigbee_3.0_USB_Dongle_Plus_...-if00-port0`
- Z2M 어댑터 타입: **`zstack`**

## 설치 & 기동 (sudo 필요)
Docker가 없으면 먼저 설치:
```bash
curl -fsSL https://get.docker.com -o /tmp/get-docker.sh && sudo sh /tmp/get-docker.sh
sudo usermod -aG docker $USER      # 재로그인 후 sudo 없이 docker 사용
```
스택 기동:
```bash
cd /home/nawonga/MiraiProject/dev/Home_IOT
docker compose up -d               # (그룹 적용 전이면 sudo docker compose up -d)
docker compose logs -f zigbee2mqtt # 어댑터 연결/펌웨어 버전 확인
```

## 검증 체크리스트
- `docker ps` 에 `homeiot-mosquitto`, `homeiot-zigbee2mqtt` Up
- Z2M 로그에 `Coordinator firmware version` 출력(= 동글 연결 성공)
- 컨테이너 안 장치 매핑: `docker exec homeiot-zigbee2mqtt ls -l /dev/zigbee`
- 웹 UI: `http://<PI_IP>:8080`

## 페어링
1. 웹 UI에서 **Permit join** 켜기 (Z2M 2.x는 설정파일 아닌 UI/MQTT로 제어)
2. 기기를 페어링 모드로
3. 조인되면 friendly name을 안정적인 이름으로 변경
4. **끝나면 Permit join 끄기** (보안)

## Home_IOT 연동(예정)
- Z2M는 `zigbee2mqtt/<friendly_name>` 토픽으로 상태를 publish, `.../set`으로 명령 수신.
- Home_IOT `engine.handle_json`의 zigbee 어댑터가 MQTT로 `{"state":"ON"}` 등을 publish/subscribe하도록 추가 예정.
- 로컬 스위치 자동화는 `../docs/zigbee_switch_automation.md` 참고(별도 러너).

## 주의
- `zigbee2mqtt/data/`(network key·DB), `mosquitto/data|log`는 gitignore. configuration.yaml 템플릿은 본 문서/리포 이력 참고.
- MQTT는 현재 anonymous 허용(로컬). 외부 노출 시 인증 필요.
