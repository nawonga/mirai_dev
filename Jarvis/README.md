# Jarvis (Pepper Potts)

한국어 음성 기반 **로컬-퍼스트 홈 어시스턴트 오케스트레이터**.

기본 파이프라인:

**Wakeword(Porcupine/openWakeWord) → TTS(Google/Piper) → Record(VAD) → STT(faster-whisper) → Intent(Local/Mirai_brain) → Domain → Response**

> 이 repo의 최우선 규칙은 최상위 `OPERATING.md` 및 `OPERATING_RULES.md` 입니다.

---

## Quick Start

### 1) venv 활성화

```bash
cd /home/nawonga/MiraiProject/dev/Jarvis
source venv/bin/activate

### 2) 실행

```bash
# wakeword 포함 실행 (PV_ACCESS_KEY 필요)
PYTHONPATH=src python -m jarvis.main
```

Wakeword 없이(dev):

```bash
JARVIS_SKIP_WAKEWORD=1 PYTHONPATH=src python -m jarvis.main
```
## 문서 (필독 우선순위)

1. `ARCHITECTURE.md` — 설계 헌법(시스템이 어떻게 생겼는가)
2. `OPERATING_RULES.md` — 운영/안전 헌법(절대 규칙)
3. `RECOVERY_GUIDE.md` — 재부팅/세션 단절 후 2분 복구
4. `MILESTONES.md` — 어떤 단계까지 검증되었는가
5. `CHANGELOG.md` — 릴리즈 단위 변경 기록
6. `ROADMAP.md` — 앞으로 갈 방향

추가 문서:
- `README_LOCAL_SETUP.md` — Raspberry Pi 로컬 셋업/스모크 테스트 상세
- `docs/` — 하드웨어/오디오/안전/계약 문서

## 설정

런타임 설정은 `config/settings.yaml`이 single source of truth 입니다.

---

## 라이선스/크레딧

- Wakeword: Picovoice Porcupine
- STT: faster-whisper
- TTS: Piper / eSpeak-ng
- Core Logic: Mirai_brain (Gemini 2.5 Flash)