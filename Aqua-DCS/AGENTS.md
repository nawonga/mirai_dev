# AGENTS.md - Aqua-DCS Router

Aqua-DCS 작업 전에는 이 문서를 먼저 읽고, 이어서 `OPERATING_RULES.md` 를 읽는다.

상세 규칙:
- `/home/nawonga/MiraiProject/dev/Aqua-DCS/OPERATING_RULES.md`
- 상위 시스템 헌법: `/home/nawonga/MiraiProject/dev/OPERATING.md`

## 1) 프로젝트 역할
Aqua-DCS는 45cm 큐브 해수어항의 **센서 수집 / 저장 / 모니터링 / 제어** 도메인 시스템이다.
DCS(Distributed Control System)와 ESD(Emergency Shutdown)를 분리하고, **fail-safe 가 모든 결정의 1순위**다.

상위 의도 해석은 Mirai_brain(Gemini 2.5 Flash) 이 담당하고, Aqua-DCS 는 구조화된 요청을 받아 deterministic 하게 실행/응답한다.

## 2) canonical 경로
- 정본 (dev): `/home/nawonga/MiraiProject/dev/Aqua-DCS`
- 운영 (prod): `/home/nawonga/MiraiProject/prod/Aqua-DCS` *(검증 완료 후 배포)*
- Git 원본: `https://github.com/nawonga/aqua-DCS`
- 실시간 스냅샷: `/run/aqua-dcs/latest.json` (RuntimeDirectory)
- DB: `/home/nawonga/MiraiProject/dev/Aqua-DCS/data/aqua.db`

## 3) 구조 (2026-05-30 clone 기준)
```
src/dcs/
  collector/    # 센서 폴링 → DB 적재 + latest.json 갱신 (데몬)
  drivers/      # 하드웨어 추상화 (DS18B20 sysfs, ADS1115/i2c, pH/EC/light)
  storage/      # SQLite 모델 + 쿼리
  services/     # sampler, control, calibrate, alarms, export, filters
  web/          # Flask 대시보드 + API
  jobs/         # backup, weekly_report
  analytics/    # weekly_report
systemd/        # aqua-dcs-collector.service, aqua-dcs-web.service
scripts/        # install.sh, init_db.sh, dev_run.sh
config/         # settings.yaml
```

## 4) 이 프로젝트에서 AI가 특히 기억할 것
- **Mirai_brain / Jarvis 가 Aqua-DCS 의 안전 판단을 대체할 수 없다.** ESD 로직은 Aqua-DCS 내부에서 deterministic 하게 결정한다.
- **상위 계층에서의 GPIO 직접 제어, 센서 직접 읽기, ESD 우회는 금지**한다. 모든 외부 호출은 Aqua-DCS API/CLI 계약을 통과해야 한다.
- AI 는 제어 판단의 단독 주체가 아니라 **보조 / 요약 / 분석** 역할에 머문다.
- **구조 정의, 책임 분리, 인터페이스 합의**를 구현보다 먼저 한다.
- 코드 변경 시 dev 에서만 작업, prod 디렉토리는 직접 수정 금지 (`OPERATING.md §3`).

## 5) 작업 원칙
- 운영 프로세스는 **systemd** 로 관리 (`aqua-dcs-collector`, `aqua-dcs-web`). tmux/screen 등 ad-hoc 데몬화 금지.
- **raw / 보정 / 분석** 결과를 분리 저장한다.
- fail-safe / 장애 대응 / 센서 보정 기록을 문서화한다.
- 하드웨어 접근 그룹: `i2c spi gpio dialout` (nawonga 보유, systemd 유닛 `SupplementaryGroups` 명시).

## 6) Mirai_brain ↔ Aqua-DCS 연동점 (예정)
Mirai_brain 이 자연어로부터 Aqua-DCS 요청을 라우팅할 때 사용할 계약 표면:
- HTTP API: Flask `web/` 모듈 — 현재 routes_api.py, routes_control.py, routes_events.py, routes_export.py 가 골격
- 읽기 전용 조회: `/run/aqua-dcs/latest.json` (수온/pH/EC/조도 등 최신 스냅샷)
- 쓰기 (제어/캘리브레이션): API 경유 only — 직접 GPIO / DB 변경 금지

*Home_IOT 의 `Mirai_brain ↔ Home_IOT` JSON 명령 계약(`docs/JSON_COMMAND_SCHEMA.md`)에 준해 Aqua-DCS 측 계약도 정합성 유지.*

## 7) 하지 말 것
- 즉흥적인 구조 변경
- DCS / ESD 책임 혼합 (안전 로직을 일반 service 에 섞기)
- 운영 시스템에 대한 임시방편식 패치 누적
- Jarvis 쪽에 Aqua-DCS 내부 로직을 박아넣기
- 검증되지 않은 코드를 prod/ 에 직접 배치
