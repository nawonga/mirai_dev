# Aqua-DCS — Milestones

이 문서는 **세션 복구/진행상황 추적**을 위한 마일스톤 로그입니다.

규칙:
- 마일스톤마다 **목표 / 결과 / 변경 파일 / 실행 방법 / 트러블슈팅**을 기록합니다.

---

## M1 — DS18B20 온도센서(GPIO 1-Wire) 드라이버 연결

### 목표
- Raspberry Pi에 연결한 **DS18B20** 온도센서를 Aqua-DCS에서 읽어
  기존 collector의 dummy temperature 값을 실제 센싱값으로 대체

### HW
- 센서: DS18B20 (1-Wire)
- 연결: 데이터 라인 **물리 핀 7(BCM GPIO4)**

핀 표기 규칙(필수):
- 문서/설정에 항상 **physical pin 번호 + BCM 번호를 같이 적기**
  - 예: `physical pin 7 (BCM GPIO4)`

### 결과
- `/sys/bus/w1/devices/28-*/w1_slave`에서 CRC=YES 및 `t=xxxxx` 출력 확인

### 부팅 설정(중요)
`/boot/firmware/config.txt`:
```ini
# Enable 1-Wire for DS18B20 temperature sensor on physical pin 7 (BCM GPIO4)
dtoverlay=w1-gpio-pi5,gpiopin=4
```

### 빠른 센서 확인
```bash
ls -la /sys/bus/w1/devices
cat /sys/bus/w1/devices/28-*/w1_slave
```

### 다음 단계
- `src/dcs/drivers/temperature_ds18b20.py` 구현
- `src/dcs/collector/main.py`에서 temperature 값을 DS18B20로 대체

### Smoke test
```bash
cd /home/nawonga/Projects/aqua-dcs
./scripts/temp_smoke_test.sh
```

센서 ID 고정(권장, 센서 2개 이상 대비):
```bash
export AQUA_DS18B20_ID="28-000000833080"
./scripts/temp_smoke_test.sh
```
