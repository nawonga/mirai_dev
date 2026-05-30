# Home_IOT Alias / Action Mapping Standard

## Purpose
음성 표현, 장치 별칭, 실행 액션 id를 분리해서 관리한다.
새 기기 학습/등록이 기존 제어 흐름을 깨지 않도록 canonical id 기반으로 운영한다.

## 1) Layers

### A. Spoken aliases
사람이 말하는 다양한 표현.
예:
- 티비
- TV
- 텔레비전
- 거실 티비

### B. Canonical device id
시스템 내부에서 안정적으로 쓰는 id.
예:
- `tv`
- `aircon`
- `fan`
- `living_room_light`

### C. Canonical action id
시스템 내부에서 안정적으로 쓰는 액션 id.
예:
- `power`
- `volume_up`
- `volume_down`
- `mute`
- `temp_up`
- `temp_down`

## 2) Normalization rule
- 음성 표현은 먼저 alias map으로 canonical device id/action id 후보로 변환한다.
- 실행은 canonical id 기준으로만 한다.
- registry에는 canonical id만 저장한다.
- active runtime path도 canonical id와 action id 기준으로 연결한다.

## 3) Power action policy
기본 `power` 는 토글형 장치를 위한 범용 액션이다.
향후 장치가 명확한 on/off 상태 확인이 가능하면 아래를 추가로 지원한다:
- `power_on`
- `power_off`

정책:
- IR TV처럼 토글 리모컨만 있으면 `power` 사용
- Zigbee/SmartThings처럼 상태 기반 제어가 가능하면 `power_on` / `power_off` 우선 지원

## 4) Example baseline mapping

### Devices
- `tv`: `tv`, `티비`, `TV`, `텔레비전`
- `aircon`: `에어컨`, `aircon`, `ac`
- `fan`: `선풍기`, `fan`
- `living_room_light`: `거실등`, `거실 조명`, `거실 불`

### Actions
- `power`: `전원`, `켜`, `꺼`, `켜줘`, `꺼줘`
- `volume_up`: `볼륨 올려`, `소리 키워`, `음량 올려`
- `volume_down`: `볼륨 내려`, `소리 줄여`, `음량 내려`
- `mute`: `음소거`, `뮤트`
- `temp_up`: `온도 올려`, `더 따뜻하게`
- `temp_down`: `온도 내려`, `더 시원하게`

## 5) Stability rule
- alias 추가는 가능하지만 canonical id는 쉽게 바꾸지 않는다.
- 기존 device/action id 변경은 하위 호환성 영향 검토 후에만 한다.
- 새 장치 추가는 기존 장치 id/action id를 건드리지 않는다.
