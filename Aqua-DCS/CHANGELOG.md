# Changelog (Aqua-DCS)

All notable code changes to this project will be documented in this file.

---

## [Unreleased]

### Added
- `MILESTONES.md` for session restore and milestone tracking.

### Changed
- Workspace/Jarvis side phrase routing에서 수조/아쿠아/온도 관련 발화를 `aqua_dcs` 성격의 요청으로 분류하는 기반을 보강했다.
- Aqua-DCS SQLite 데이터(`data/aqua.db`)를 기준으로 최근 5일 온도 차트를 생성해 텔레그램으로 공유하는 운영 흐름을 확인했다.

### Fixed
- DS18B20 1-Wire GPIO pin mapping confusion:
  - Physical pin 7 is **BCM GPIO4**, not BCM7.
  - Use `dtoverlay=w1-gpio-pi5,gpiopin=4` in `/boot/firmware/config.txt`.

### Changed
- DS18B20 driver/collector can pin a specific sensor id via `AQUA_DS18B20_ID`.
