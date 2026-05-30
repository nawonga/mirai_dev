# PipeWire / ALSA Notes

> 검증된 장치별 셋업은 `jabra_speak510.md` 참고 (2026-05-25 Jabra SPEAK 510 양방향 검증 완료).

Jarvis는 Raspberry Pi + PipeWire 환경에서 오디오 장치가 종종 **busy** 상태가 되는 이슈를 겪었습니다.

## 핵심 요약
- 녹음/캡처는 Porcupine(pvrecorder)와 STT(arecord)가 같은 장치를 동시에 열면 충돌할 수 있습니다.
- 재생은 `aplay`가 raw hw device를 열려다가 실패할 수 있어, 가능하면 `pw-play`를 우선 사용합니다.

## 현재 설정(예)
`config/settings.yaml`:
- input: `plughw:CARD=USB,DEV=0`
- output: `default:CARD=USB`

## 운영 팁
- 장치 목록 확인:
  ```bash
  arecord -l
  aplay -l
  aplay -L
  ```
