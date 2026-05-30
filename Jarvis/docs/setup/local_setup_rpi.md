# Local Setup Notes (Raspberry Pi)

원본 문서: 기존 `README_LOCAL_SETUP.md` 내용을 `docs/`로 재분류한 것입니다.

Jarvis는 **local-first**:

Wake word (Porcupine) → TTS greeting (Piper) → Record audio → STT (faster-whisper) → Intent routing → Domain execution.

이 문서는 **Raspberry Pi (aarch64)** + **Jabra SPEAK 510** USB mic/speaker 기준의 동작 설정을 기록합니다.

---

## Audio devices

ALSA device string을 사용합니다.

- Input/Output device (Jabra):

```bash
plughw:CARD=USB,DEV=0
```

장치 목록:

```bash
arecord -l
aplay -l
aplay -L
```

### PipeWire note (important)

Raspberry Pi + PipeWire 환경에서는 raw ALSA hardware device(`hw:`/`plughw:`)가 busy일 수 있습니다.
재생은 PipeWire-native 툴을 선호합니다:

```bash
pw-play some.wav
```

Jarvis의 TTS 재생은 가능하면 `pw-play`를 사용하도록 구성합니다.

---

## Python environment

프로젝트 venv 생성 및 의존성 설치:

```bash
cd /home/nawonga/Projects/jarvis

# system deps (for PyAudio build)
sudo apt-get update -y
sudo apt-get install -y portaudio19-dev python3-dev build-essential

python -m venv .venv
source .venv/bin/activate

python -m pip install -U pip setuptools wheel
python -m pip install -e .
```

---

## Korean female TTS (Piper + Mimic3 KSS ONNX)

동작 확인된 한국어 신경망 음성은 Mimic3 KSS voice(ONNX 변환본)를 사용합니다.

### Model files

- 다운로드:
  - https://huggingface.co/csukuangfj/vits-mimic3-ko_KO-kss_low

- 저장 위치:
  - `data/models/piper/bakeoff/ko_KO-kss_low.onnx`

레포의 `*.onnx.json`은 학습용 config라 Piper voice config로는 사용할 수 없습니다.
`tokens.txt`로부터 Piper-compatible config를 생성해 사용합니다:

- `data/models/piper/bakeoff/ko_KO-kss_low.piper.json`

### One-shot synth + play

```bash
cd /home/nawonga/Projects/jarvis
TEXT="페퍼입니다. 무엇을 도와드릴까요?"

printf "%s" "$TEXT" | ./bin/piper \
  --model data/models/piper/bakeoff/ko_KO-kss_low.onnx \
  --config data/models/piper/bakeoff/ko_KO-kss_low.piper.json \
  --output_file data/cache/tts_test.wav

aplay -D plughw:CARD=USB,DEV=0 data/cache/tts_test.wav
```

---

## STT smoke test (record → faster-whisper transcript)

```bash
cd /home/nawonga/Projects/jarvis
source .venv/bin/activate

PYTHONPATH=src python - <<"PY"
from jarvis.config.loader import load_settings
from jarvis.core.speech.stt import SttConfig, SttEngine, record_wav

s = load_settings()
wav = s.paths.cache_dir / "stt_smoke.wav"

record_wav(wav, seconds=4, device=s.audio.input_device, rate=16000)

stt = SttEngine(SttConfig(
    model_size=s.stt_engine.model_size,
    device=s.stt_engine.device,
    compute_type=s.stt_engine.compute_type,
    language=s.stt_engine.language,
))
stt.start()
print(stt.transcribe_wav(wav))
PY
```

---

## Run Jarvis

```bash
cd /home/nawonga/Projects/jarvis
source .venv/bin/activate

# ensure PV_ACCESS_KEY is exported
export PV_ACCESS_KEY=...

PYTHONPATH=src python -m jarvis.main
```

---

## Gemini (Google AI Studio) integration (optional)

local-first를 유지하면서, 로컬 라우팅으로 처리 불가한 일반 Q/A는 Gemini로 fallback 할 수 있습니다.

### 1) Store API key

- `~/.config/jarvis/secrets.env`

```bash
GEMINI_API_KEY=YOUR_GOOGLE_AI_STUDIO_KEY
```

### 2) Enable in settings

`config/settings.yaml`:

```yaml
gemini:
  enabled: true
  model: "gemini-flash-latest"
  timeout_seconds: 20
  max_output_tokens: 512
```

### 3) Smoke test

```bash
cd /home/nawonga/Projects/jarvis
source .venv/bin/activate
chmod +x scripts/gemini_smoke_test.sh
./scripts/gemini_smoke_test.sh
```

---

## Google Cloud TTS (primary) + local fallback

현재 기본 컨셉은:
- **Primary**: Google Cloud TTS
- **Fallback**: 로컬 Piper (클라우드 장애/지연/인증 실패 시)

### 1) Service Account JSON 배치 (git 밖)

```bash
mkdir -p /home/nawonga/.config/jarvis
mv <YOUR_GCP_SERVICE_ACCOUNT_JSON>.json /home/nawonga/.config/jarvis/gcp-tts-sa.json
chmod 600 /home/nawonga/.config/jarvis/gcp-tts-sa.json
```

### 2) secrets.env에 credentials 경로 등록

`~/.config/jarvis/secrets.env`:

```bash
GOOGLE_APPLICATION_CREDENTIALS=/home/nawonga/.config/jarvis/gcp-tts-sa.json
```

Jarvis는 시작 시 `~/.config/jarvis/secrets.env`를 자동 로드합니다.

### 3) settings 확인

`config/settings.yaml`:

```yaml
tts_engine:
  provider: "google"
  google_language_code: "ko-KR"
  google_voice_name: "ko-KR-Chirp3-HD-Aoede"
  google_speaking_rate: 1.0
  google_pitch: 0.0
  wake_response_cache_wav: "data/cache/wake_response_google.wav"
```

### 4) Wake 응답 지연 최소화

앱 시작 시 wake 응답 문구(`assistant.wake_response`)를 Google TTS로
한 번 합성해 `wake_response_cache_wav`에 저장하고,
wake 시에는 이 캐시를 즉시 재생합니다.

즉, 네트워크 지연이 있어도 wake 첫 반응 지연을 줄일 수 있습니다.

---

## Wake word ("헤이페퍼") smoke test

Porcupine wakeword + TTS 반응을 가장 빠르게 검증하는 방법입니다.

```bash
cd /home/nawonga/Projects/jarvis
source .venv/bin/activate

export PV_ACCESS_KEY=...
./scripts/wakeword_smoke_test.sh
```

### Note: Korean wakeword requires Korean Porcupine model (.pv)

- keyword: `config/wakeword/hey_pepper_ko.ppn`
- model: `config/wakeword/porcupine_params_ko.pv`

---

## Run without wake word (dev mode)

```bash
cd /home/nawonga/Projects/jarvis
source .venv/bin/activate

JARVIS_SKIP_WAKEWORD=1 PYTHONPATH=src python -m jarvis.main
```

추가 로그:

```bash
PYTHONPATH=src python -m jarvis.main --log-level DEBUG
```
