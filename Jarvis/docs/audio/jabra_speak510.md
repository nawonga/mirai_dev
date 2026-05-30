# Jabra SPEAK 510 — 오디오 셋업 기록 (검증 완료)

> 검증일: 2026-05-25 / 환경: Raspberry Pi 5, PipeWire 1.4.2, kernel 6.18 (rpi)
> 결론: **별도 드라이버 설치 불필요.** USB Audio Class 장치라 `snd-usb-audio`가 자동 인식. 스피커·마이크 양방향 동작 검증 완료.

## 1. 장치 식별
- 제품: **Jabra SPEAK 510 USB**
- USB ID: `0b0e:0422`
- 커널: `snd-usb-audio` 자동 바인딩 (dmesg에 "Jabra SPEAK 510 USB" 열거 확인)
- ALSA: **card 2 = `USB`**, playback/capture 모두 `device 0`
  - 재생: `card 2: USB [Jabra SPEAK 510 USB], device 0`
  - 녹음: `card 2: USB [Jabra SPEAK 510 USB], device 0`
- PipeWire 노드:
  - Sink(스피커): `alsa_output.usb-0b0e_Jabra_SPEAK_510_USB_<serial>-00.analog-stereo` (FL,FR)
  - Source(마이크): `Jabra SPEAK 510 USB Mono`

## 2. 기본 라우팅 / 볼륨 (현재 설정)
- WirePlumber가 연결 시 자동으로 **기본 sink + 기본 source**로 선택함.
- **Sink(스피커) 볼륨: 1.00**
- **Source(마이크) 볼륨: 0.75** ← 게인 1.00에서 녹음 피크가 −0.1 dB로 **클리핑 직전**이라, STT 헤드룸 확보 위해 낮춤.
- 재부팅 후 기본 장치가 아니면 수동 지정:
  ```bash
  wpctl set-default <sink-id>     # wpctl status 에서 id 확인
  wpctl set-default <source-id>
  ```

## 3. 검증 방법 (재현용)
스피커:
```bash
ffmpeg -f lavfi -i "sine=frequency=660:duration=3" -ar 48000 -ac 2 /tmp/t.wav -y
pw-play /tmp/t.wav            # 톤이 들리면 OK
```
마이크 (객관적 레벨 분석 포함):
```bash
timeout -s INT 6 pw-record --channels 1 --rate 48000 /tmp/m.wav   # 6초 녹음
ffmpeg -i /tmp/m.wav -af volumedetect -f null - 2>&1 | grep -iE "mean_volume|max_volume"
pw-play /tmp/m.wav           # 본인 목소리 재생 확인
```
- 검증 결과: 녹음 5.95s/48kHz/mono, **mean_volume −28.6 dB**(무음 −91dB 대비 정상 캡처), 재생 시 음성 또렷.

## 4. 주의사항 (Jarvis 상시 구동 관점)
- **내장 배터리 + 블루투스 장치.** 상단 배터리 아이콘 **빨간불 = 배터리 부족**.
  - USB 연결 시 충전됨. **항상 전력 넉넉한 USB 포트에 상시 연결** 권장.
  - 배터리가 거의 없으면 **절전 상태**로 빠져, idle 후 **첫 재생이 끊기거나 지연**될 수 있음 (실제 관측됨 — 첫 톤 미출력 → 재시도 시 정상).
  - 구형 모델이라 배터리 노후 시 충전해도 빨간불이 남을 수 있으나, **USB 상시 급전이면 오디오 기능엔 무관**.
- **블루투스 모드 주의:** 폰과 BT 연결돼 있으면 USB 스트림이 스피커로 안 나갈 수 있음. USB 사용 시 BT 미연결 권장.
- **device-busy:** PipeWire가 장치를 점유하므로 `aplay`/`arecord`로 raw hw를 직접 열면 충돌 가능. **`pw-play`/`pw-record` 우선 사용**. (`pipewire_notes.md` 참고)

## 5. settings.yaml 매핑 (Jarvis 코드 연동 시)
ALSA 직접 경로를 쓸 경우(카드명 `USB` 기준):
```yaml
audio:
  input:  "plughw:CARD=USB,DEV=0"
  output: "default:CARD=USB"
```
- 단, 본 repo는 device-busy 회피를 위해 재생은 PipeWire(`pw-play`) 경로를 우선한다.
