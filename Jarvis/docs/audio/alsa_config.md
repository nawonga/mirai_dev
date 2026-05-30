# ALSA Config (Draft)

## 장치 확인

```bash
arecord -l
aplay -l
aplay -L
```

## 현재 repo 기본값
`config/settings.yaml`:
- input: `plughw:CARD=USB,DEV=0`
- output: `default:CARD=USB`
