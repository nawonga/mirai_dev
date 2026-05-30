# Jarvis (Pepper Potts) — Milestones

이 문서는 **세션이 끊기거나 새 세션에서 다시 작업을 이어갈 때** 빠르게 맥락을 복구하기 위한 마일스톤 로그입니다.

규칙:
- 마일스톤마다 **목표 / 결과 / 변경 파일 / 실행 방법 / 트러블슈팅**을 기록합니다.

---

## M1 — 로컬 음성 파이프라인 MVP (Wakeword → TTS → Record → STT)

### 목표
- Raspberry Pi(aarch64)에서 **클라우드 없이** 음성 파이프라인을 최소 단위로 동작시키기
- 웨이크워드: Porcupine
- TTS: Piper(고품질 한국 여성 음성)
- STT: faster-whisper 로컬

### HW/OS
- Raspberry Pi (aarch64)
- Jabra SPEAK 510 USB mic/speaker
- ALSA device: `plughw:CARD=USB,DEV=0`
- PipeWire 설치됨

---

### 결과(성공 기준)
- 한국어 여성 음성 TTS가 깨지지 않고 정상 발음으로 재생됨
- `faster-whisper`로 로컬 STT가 텍스트를 생성함
- 웨이크워드 **"헤이페퍼"** 감지 시 TTS 응답이 재생됨

---

## 1) TTS (Piper) — 한국어 고품질 음성 고정

### 문제
- 기존 Piper 한국어 모델(`piper-kss-korean`)은 WAV 생성/재생은 되지만 **발음이 외계어처럼 깨짐**

### 해결
- HuggingFace `csukuangfj/vits-mimic3-ko_KO-kss_low` ONNX 모델을 사용
- 레포의 `*.onnx.json`은 Piper voice config가 아니라 학습용 config라 그대로 쓰면 Piper가 크래시
- `tokens.txt`로부터 Piper가 이해하는 `phoneme_id_map`을 생성하여
  `ko_KO-kss_low.piper.json`을 만들어 Piper 1.2.0에서 정상 합성되도록 구성

### 관련 파일
- 모델: `data/models/piper/bakeoff/ko_KO-kss_low.onnx`
- Piper voice config(생성본): `data/models/piper/bakeoff/ko_KO-kss_low.piper.json`
- 설정 반영: `config/settings.yaml` (`tts_engine.provider: piper`)

### TTS 단독 테스트
```bash
cd /home/nawonga/MiraiProject/dev/jarvis
TEXT="페퍼입니다. 무엇을 도와드릴까요?"

printf "%s" "$TEXT" | ./bin/piper \
  --model data/models/piper/bakeoff/ko_KO-kss_low.onnx \
  --config data/models/piper/bakeoff/ko_KO-kss_low.piper.json \
  --output_file data/cache/tts_test.wav

aplay -D plughw:CARD=USB,DEV=0 data/cache/tts_test.wav
```

---

## M2 — STT 단독 검증 (faster-whisper, dev)

### 목표
- dev 환경 Jarvis venv에서 **마이크 → 로컬 STT 전사** 파이프라인을 최소 단위로 동작/검증

### 결과(성공)
- Jabra SPEAK 510 마이크로 한국어 발화를 정확히 전사:
  `한국어를 또박또박 말해봅시다. 잘 들립니까?`
- 언어 `ko` 감지(p=1.00). `small` 모델, CPU/`int8`. 오디오 7.9s → 전사 9.9s (**~1.25× 실시간**)

### 변경 파일
- `src/jarvis/__init__.py`, `src/jarvis/stt.py` (신규)
- `requirements.txt` (의존성 고정: faster-whisper 1.2.1, ctranslate2 4.7.2, av, onnxruntime, tokenizers, numpy …)

### 실행 방법
```bash
cd /home/nawonga/MiraiProject/dev/Jarvis
PYTHONPATH=src venv/bin/python -m jarvis.stt --seconds 8 --model small
# 기존 wav 전사: --file path.wav
```

### 트러블슈팅
- 첫 시도에 문장 앞부분이 잘림 → **녹음 시간을 늘리고 신호음 직후 발화**하면 해결(타이밍 이슈, 인식 자체는 정상).
- `onnxruntime ... GetGpuDevices /sys/class/drm` 경고는 **무해**(GPU 없음 → CPU 폴백).
- 녹음은 `pw-record`(PipeWire) 경로 사용 — raw ALSA 직접 접근 device-busy 회피.
- 성능이 실시간보다 약간 느림 → 응답성이 더 필요하면 `base` 모델 검토(한국어 정확도는 하락).

---

## M3 — Wakeword 검증 (Porcupine 한국어 "향다나", dev)

### 목표
- Porcupine으로 한국어 커스텀 웨이크워드 "**향다나**" 감지를 dev에서 동작/검증

### 결과(성공)
- "향다나" 발화 시 즉시 감지(#1) 확인. sample_rate=16000, frame=512, sensitivity=0.5.

### 변경 파일
- `src/jarvis/wakeword.py` (신규) — Porcupine create + PvRecorder 루프, `--once/--timeout/--device/--list` 지원
- `Hyangdana_ko_raspberry-pi_v4_0_0.ppn` (사용자 제공, repo 루트)
- `data/models/porcupine/porcupine_params_ko.pv` (Picovoice repo에서 다운로드, gitignore됨)
- `.env` (PV_ACCESS_KEY, gitignore됨)
- `requirements.txt` (pvporcupine 4.0.2, pvrecorder 1.2.7 추가)

### 실행 방법
```bash
cd /home/nawonga/MiraiProject/dev/Jarvis
PYTHONPATH=src venv/bin/python -m jarvis.wakeword --list                  # 입력 장치 목록
PYTHONPATH=src venv/bin/python -m jarvis.wakeword --device 1 --once --timeout 30
```

### 트러블슈팅 / 주의
- **한국어 키워드는 한국어 모델(`porcupine_params_ko.pv`) 필수** — 기본 번들은 영어뿐. `create(model_path=...)`로 지정.
- pvporcupine **4.0.2**가 .ppn `v4_0_0`과 버전 일치해야 함.
- **장치 인덱스 주의**: `--list`에서 `[0] Monitor of ...`(스피커 루프백), `[1] Jabra ... Mono`(실제 마이크). 모니터를 잡으면 내 목소리 대신 스피커 출력을 듣게 되므로 **마이크([1]) 명시 권장**.
- 액세스 키는 코드 하드코딩 금지 — `.env`의 `PV_ACCESS_KEY`에서 로드.
- **device-busy 주의**: Porcupine(PvRecorder)이 마이크를 점유하므로, 이후 STT와 동시 사용 시 마이크 경합 발생 가능 → 통합 시 캡처 스트림 공유/전환 전략 필요(docs/audio/pipewire_notes.md).

---

## M4 — Google STT/TTS 운영 엔진 (+ Whisper fallback)

### 목표
- 운영 기본 STT/TTS를 **Google Cloud**로 두고, STT는 실패 시 **Whisper로 자동 폴백**

### 결과(성공)
- **TTS↔STT 라운드트립**(마이크 없이): TTS 합성 음성을 STT가 정확히 되받음(conf 0.66).
- **TTS 재생**: `ko-KR-Wavenet-A`(여성) 음성으로 Jabra 발화 정상.
- **실마이크 auto 경로**: engine=google, conf 0.85, **2.6초**에 전사(Whisper ~10초 대비 빠름).

### 변경 파일
- `src/jarvis/gcloud.py` (자격증명 로더 — `.env`의 `GOOGLE_APPLICATION_CREDENTIALS` 또는 기본 키)
- `src/jarvis/google_stt.py` (Google STT, ko-KR, LINEAR16 WAV)
- `src/jarvis/tts.py` (Google TTS, 기본 voice `ko-KR-Wavenet-A`, `pw-play` 재생, `--list-voices`)
- `src/jarvis/stt.py` (`transcribe_with_fallback`, `--engine auto|google|whisper` 추가)
- `requirements.txt` (google-cloud-speech 2.39.0, google-cloud-texttospeech 2.36.0)

### 실행 방법
```bash
cd /home/nawonga/MiraiProject/dev/Jarvis
PYTHONPATH=src venv/bin/python -m jarvis.tts "안녕하세요"                # TTS 발화
PYTHONPATH=src venv/bin/python -m jarvis.tts --list-voices              # 음성 목록
PYTHONPATH=src venv/bin/python -m jarvis.google_stt --seconds 6         # Google STT 단독
PYTHONPATH=src venv/bin/python -m jarvis.stt --engine auto --seconds 6  # 운영(Google→Whisper 폴백)
```

### 주의 / 트러블슈팅
- 자격증명: `google-key-new.json`(권한 600, gitignore). 코드 하드코딩 금지 — `gcloud.get_credentials()`가 로드.
- 엔진 선택: `--engine auto`가 운영 기본(Google 우선, 예외/빈결과 시 Whisper). `google`/`whisper`로 강제 가능.
- 언어코드: Whisper식 `ko` ↔ Google식 `ko-KR` 변환은 `stt._bcp47()`가 처리.
- Google STT 동기 recognize는 ~60초/10MB 제한(짧은 발화용). 장문/스트리밍은 추후 streaming API 검토.
- **폴백 경로는 코드상 구현됐으나 강제 검증(=Google 의도적 실패)은 아직 미수행** — 통합 단계에서 네트워크 차단 시나리오로 확인 권장.

---

## M5 — 미니 통합 루프 (Wakeword → STT → TTS)

### 목표
- 음성 I/O 레이어를 하나의 루프로 연결: "향다나" 감지 → 발화 녹음·전사 → 응답 발화
- **device-busy 해소**: 웨이크워드 감지 후 마이크를 반납한 뒤 STT가 사용

### 결과(성공)
- 1턴 전체 정상: 마이크 자동탐색(idx 1) → "향다나" 감지 → STT(google) **"오늘 날씨 어때?"** 정확 인식 → TTS echo 응답까지 예외 없이 완료.
- Porcupine(PvRecorder) ↔ STT(pw-record) **마이크 충돌 없음** 확인.

### 변경 파일
- `src/jarvis/main.py` (신규) — 통합 엔트리포인트(`--once/--wake-timeout/--device/--seconds`)
- `src/jarvis/wakeword.py` — `find_mic_device()`, `create_porcupine()`, `detect_once()`(감지 후 recorder 해제) 추가

### 실행 방법
```bash
cd /home/nawonga/MiraiProject/dev/Jarvis
PYTHONPATH=src venv/bin/python -m jarvis.main                      # 무한 루프
PYTHONPATH=src venv/bin/python -m jarvis.main --once --wake-timeout 40
```

### device-busy 해소 방식 (핵심)
- Porcupine 인스턴스는 루프 전체에서 1회 생성·재사용.
- 매 턴마다 `detect_once()`가 **PvRecorder를 새로 열고 감지 후 `finally`에서 stop/delete로 마이크 반납** → 직후 `stt.record()`(pw-record)가 같은 마이크를 점유 가능.
- 마이크([0]=Monitor 회피) 인덱스는 `find_mic_device()`로 자동 선택.

### 다음 단계
- Intent 레이어(`src/jarvis/intent.py`): STT/텍스트 결과 → 의도 분기. echo 응답을 실제 동작으로 교체.
- 텍스트 명령 API(`docs/api_contracts/text_command_api.md`)도 같은 Intent 단계로 합류.

---

## M6 — Intent 레이어 (로컬 규칙 파서 + Mirai_brain 핸드오버 스켈레톤)

### 목표
- Local-First 규칙 파서로 단순 의도를 즉시 처리하고, 미해결 의도는 Mirai_brain으로 핸드오버
- 통합 루프(main.py)의 echo 응답을 Intent 분기로 교체

### 결과(성공)
- 배터리 테스트(마이크 없이) 7문장 정확 분류:
  - 로컬: `time.now`/`date.today`/`greeting`/`thanks`/`system.stop`
  - 핸드오버: "오늘 날씨 어때?", "거실 불 켜줘" → `handover.pending`(Mirai_brain 스텁)
- 라이브 통합: "향다나" → STT(google) "지금 몇 시야?" → `time.now`(local) → "지금은 오후 9시 53분이에요." 발화까지 정상.

### 변경 파일
- `src/jarvis/intent.py` (신규) — `Intent` dataclass, `parse_local()`, `parse()`(Local-First→핸드오버)
- `src/jarvis/mirai_brain.py` (신규) — 핸드오버 클라이언트. 미가동 시 스텁, `.env`의 `MIRAI_BRAIN_URL` 설정 시 `POST {url}/intent` 호출(미검증 경로)
- `src/jarvis/main.py` — echo → `intent.parse()` 분기, `system.stop` 의도 시 루프 종료

### 실행 방법
```bash
PYTHONPATH=src venv/bin/python -m jarvis.intent "지금 몇 시야?"   # 파서 단독
PYTHONPATH=src venv/bin/python -m jarvis.main --once --wake-timeout 40
```

### 설계 메모
- Local-First 대상(즉시 처리): 인사/감사/종료/시간/날짜. (시간·날짜는 §6에 따라 로컬 계산)
- 그 외(데이터 필요·복합·모호): `mirai_brain.resolve(text, context)`로 위임 → 표준 dict(`intent/route/entities/confidence/resolved_by/message`) 반환.
- 종료 키워드는 device "꺼줘"와 충돌 피하려 `그만/종료/중지/스톱/끝내`로 한정.

### 다음 단계
- Mirai_brain 실제 구현 시 스텁 교체(REST 계약은 이미 자리 잡음).
- 도메인 라우팅 확장(home_iot/aqua_dcs/personal_service) 및 텍스트 명령 API(`docs/api_contracts/text_command_api.md`)를 동일 `intent.parse()`에 연결.

---

## M7 — Jarvis systemd 사용자 데몬화 (2026-05-29)

### 목표
- Jarvis 를 systemd `--user` 데몬으로 supervise → 부팅 시 자동 기동, 크래시 자동 재시작, PipeWire 사용자 세션 자연스럽게 접근.
- PS/HIOT/MB 시스템 서비스와 함께 Mirai Space 가 **음성 입력까지 포함한 완전 24/7 운영** 상태 진입.

### 결과 (2026-05-29 21:16 KST, JM-PI)
- ✅ **사용자 레벨 systemd 채택** (`~/.config/systemd/user/jarvis.service`) — PipeWire(pipewire/pipewire-pulse/wireplumber) 가 Debian 기본상 사용자 세션 단위라 시스템 레벨이면 PolicyKit/DBUS 우회 필요.
- ✅ **linger 사전 활성화 확인** (`Linger=yes` for nawonga) — 사용자 로그아웃 후에도 user manager 살아있어 데몬 24/7 유지. 추가 sudo 불필요.
- ✅ unit 정책: `Restart=always`, `RestartSec=8` (마이크 release 여유), `StartLimitBurst=5/60s` (하드 크래시 루프 차단), `After=pipewire pipewire-pulse wireplumber`.
- ✅ **`Restart=always` 의도**: 음성 "그만/종료/끝내" → Jarvis clean exit → systemd 즉시 다시 살림. 진짜 정지는 `systemctl --user stop jarvis` 만 가능.
- ✅ Google 자격증명 자동 fallback (`gcloud.py`: ENV → .env → 기본 `google-key-new.json`).
- ✅ 부팅 자동 기동 (`is-enabled=enabled`, `default.target.wants/`).
- ✅ 라이브: Main PID 10139 active, 마이크 자동 탐색 (index=1, Jabra SPEAK 510), `"[Jarvis] 웨이크워드 대기 중... ('향다나')"` 로그 — 발화 대기.

### 변경/신설 파일
- `Jarvis/systemd/jarvis.service`
- `dev/systemd/install_jarvis_user.sh` (실행 권한 부여)
- `~/.config/systemd/user/jarvis.service` → dev 트리 심볼릭링크

### 운영 명령
```bash
systemctl --user status jarvis.service
systemctl --user restart jarvis.service
journalctl --user-unit jarvis.service -f          # 실시간 (다른 SSH 세션 권장)
journalctl -t jarvis -n 50                        # SyslogIdentifier 기반 (대안)
```

### 트러블슈팅
- **마이크 무응답**: `systemctl --user status pipewire.service` 확인.
- **마이크 busy**: 크래시 직후 PvRecorder fd 미해제 케이스. `RestartSec=8` 마진으로 대부분 해소. 잔여 시 `pkill -f pw-record` 후 restart.
- **`journalctl --user -u`** 가 빈 결과: `--user-unit` 또는 `-t jarvis` 사용.
- **STT 빈 결과**: Google 자격증명 (`google-key-new.json`, 권한 600) 확인 또는 마이크 게인.

---

## M9 — 텍스트 인입 API (iOS 단축어 / 웹훅용 REST) (2026-05-30)

### 목표
- 음성(STT) 이외의 입력 경로 확보 — iOS Siri 단축어가 받아쓰기 결과 텍스트를 POST 하면 음성 경로와 **동일한 의도 추론/도메인 실행** 흐름이 동작.
- 기존 음성 파이프라인 (wakeword/오디오/STT) 와 격리된 별도 데몬으로 운영 (충돌 회피).
- `text_command_api.md` (2026-05-25 설계 초안) 그대로 구현.

### 결과 (2026-05-30 00:14 KST, 라이브 통과)
- ✅ `src/jarvis/api.py` 신설 — FastAPI, `POST /api/v1/command`, Bearer 인증, dry_run 옵션.
- ✅ Bearer 토큰 `secrets.token_urlsafe(32)` 자동 생성, `.env` 에 보관.
- ✅ Jarvis venv 에 fastapi/uvicorn/pydantic/python-dotenv 추가 설치.
- ✅ `jarvis-api.service` systemd user unit (port 8400, PipeWire 의존성 없음).
- ✅ **라이브 14 케이스 통과**:
  - 인증 실패 (토큰 없음/잘못) → 401
  - 빈 text → 422
  - Local-first (시간/날짜/인사/sleep) → 10~17ms
  - MB rule (날씨/IoT) → 25~110ms
  - MB Gemini ("오늘 저녁 뭐 먹지", **"내일 우산 챙길까"** → weather.tomorrow → PS → 실 KMA) → 1.8~2.1s
  - dry_run=true → 도메인 호출 생략, executed=false
- ✅ 음성 경로 (`jarvis.main` 데몬, port 없음) 와 별개 프로세스로 운영 → 마이크/스피커 자원 충돌 없음.
- ✅ iOS 단축어 가이드 작성 (`docs/api_contracts/text_command_api.md` §8) — 단축어 액션 순서, 토큰 확인 방법, 보안 권장, 응답 시간 기대치.

### 변경/신설 파일
- `src/jarvis/api.py`
- `systemd/jarvis-api.service`
- `requirements.txt` — fastapi/uvicorn/pydantic/python-dotenv 추가.
- `.env` — `JARVIS_API_HOST=0.0.0.0`, `JARVIS_API_PORT=8400`, `JARVIS_API_TOKEN` (gitignored).
- `docs/api_contracts/text_command_api.md` §7~8 — 구현 결과 + iOS 단축어 가이드.
- `~/.config/systemd/user/jarvis-api.service` (dev 트리 심볼릭링크).

### 실행 / 운영
```bash
# 상태
systemctl --user status jarvis-api.service
curl -sf http://127.0.0.1:8400/healthz

# 호출 예시
TOKEN=$(grep '^JARVIS_API_TOKEN=' ~/.../Jarvis/.env | cut -d= -f2)
curl -X POST http://127.0.0.1:8400/api/v1/command \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"text":"내일 우산 챙길까","source":"ios_shortcut"}'

# 로그
journalctl --user-unit jarvis-api.service -f
```

### 알려진 제약 / TODO
- `speak=true` 옵션 무시 — Jarvis 음성 데몬 (`jarvis.main`) 과 TTS 호출 경합 회피. iOS 측에서 Siri 가 발화하므로 실제 영향 없음. 비음성 호출자 (스크립트/CRON) 가 음성 응답 원하면 향후 고려.
- Audit trail (SQLite) 미통합 — 다음 단계 (`system.audit_trail`) 에서 텍스트/음성 통합 누적 로그 도입 예정.
- Rate-limit 미구현 — LAN 내 신뢰 호출자 가정. 외부 노출 시 리버스 프록시 측에서 처리.

### 트러블슈팅
- **401**: 토큰 헤더 형식 확인 (`Authorization: Bearer <토큰>`, "Bearer " 와 공백 1개).
- **503 ("API token not configured")**: `.env` 의 `JARVIS_API_TOKEN` 값 비어있음. systemd `EnvironmentFile=` 로드 확인.
- **422**: 빈 text 또는 body JSON 오류. iOS 단축어 "URL 콘텐츠 가져오기" 의 JSON 본문 검증.
- **응답이 unknown**: 음성 경로와 동일 — `intent.parse()` 가 local-first/MB 둘 다 미해결. Mirai_brain 데몬 활성 여부 확인 (`systemctl status mirai_brain`).
- **iOS 단축어가 LAN 호스트 못 찾음**: mDNS `JM-PI.local` 대신 직접 LAN IP 사용 (`192.168.0.x:8400/...`).

---

## M8 — 음성 UX 최적화 (latency · 보이스 · 연속 대화) (2026-05-29)

### 목표
- 응답 latency 단축 — wake → 응답 발화까지 현저히 빠르게.
- 매 요청마다 wake word 부르지 않고 자연스러운 멀티턴 대화.
- 보이스 품질 향상.

### 결과 (라이브 검증 완료, JM-PI)
1. **Welcome wav 캐시** (`data/welcome.wav`) — `tts.prepare_welcome_cache()` 부팅 시 1회 합성, wake 마다 즉시 재생. 멘트 "네, 향단이에요" (Wavenet-A 4.7s → **Leda 1.24s**).
2. **Streaming STT** (`google_stt.transcribe_streaming`) — Google Cloud Speech `streaming_recognize` + `single_utterance=True`. PvRecorder 32ms chunk 를 generator 로 yield, Google 이 end-of-speech 자동 감지 → 발화 끝 ~300ms 후 final. 6초 고정 녹음 폐기.
3. **TTS 응답 캐시** (`data/tts_cache/<sha256>.wav`) — 같은 텍스트(voice/rate 포함 해시 키) 재합성 회피. 시간/날씨/안내 등 반복 응답에 효과.
4. **Wake sensitivity 0.85** — Porcupine 한국어 모델 0.5(기본) → 0.85. 마이크 신호가 약간 약해도 안정 감지.
5. **Chirp3-HD Leda 보이스** — Google TTS 한국어 여성 후보 8개 비교(Wavenet/Neural2/Chirp3) → 사용자 선택. 24kHz LLM 기반 합성.
6. **연속 대화 모드** (`continued_idle_seconds=10`) — wake 1회 후 응답 → 즉시 streaming STT 재진입(welcome 재생 X) → 10초 무발화면 wake 복귀. 멀티턴 자연스러움.
7. **턴별 latency stamp** — wake/welcome/STT/intent/TTS 각 단계 시간 출력 (`turn 시작→발화 끝 X.XXs`).

### 라이브 시연 통과
- 첫 시연: "향다나" → "네, 향단이에요" → "지금 몇시야" → 응답까지 전체 wake→speak **약 5초** (이전 8~10초 대비 절감).
- 멀티턴: "향다나" → "지금 몇시야" → 응답 → *cue 없이* "내일 비 와?" → 응답 → "TV 켜줘" → 응답 → 10초 무발화 → wake 복귀. 시나리오 그대로 동작.
- 트러블슈팅: 마이크 신호 약화로 두 번째 wake 안 잡힘 → sensitivity 0.85 부스트 + welcome 짧게로 해결. Jabra Speak 510 의 노이즈 게이트/AGC 특성 영향.

### 변경/신설 파일
- `src/jarvis/tts.py` — `WELCOME_TEXT`/`WELCOME_WAV`, `prepare_welcome_cache()`, `play_welcome()`, `cached_wav_path()`, `speak(use_cache=True)`. `DEFAULT_VOICE = "ko-KR-Chirp3-HD-Leda"`.
- `src/jarvis/google_stt.py` — `transcribe_streaming(device, max_seconds)`, `STREAM_*` 상수, `--streaming` CLI.
- `src/jarvis/main.py` — `handle_turn()` 멀티턴 loop, `--continued-idle-seconds` (기본 10), `--wake-sensitivity` (기본 0.85), `--stt-max-seconds` (기본 12), 부팅 시 `prepare_welcome_cache()`, 턴별 latency stamp.
- `data/welcome.wav`, `data/tts_cache/*.wav` (gitignored 대상 — 추후 확인 필요).
- systemd unit 변경 없음 (인자 기본값으로 동작).

### 실행
```bash
# 기본 (systemd 가 자동 실행)
systemctl --user restart jarvis.service

# 인자 조정 (수동 디버그)
PYTHONPATH=src venv/bin/python -m jarvis.main \
  --wake-sensitivity 0.9 \
  --continued-idle-seconds 15 \
  --stt-max-seconds 12
```

### 트러블슈팅
- **두 번째 wake 못 잡음**: sensitivity 부족 또는 마이크 노이즈 게이트. `--wake-sensitivity 0.9` 시도.
- **응답 후 사용자 발화 무반응**: 응답 발화 끝나기 전에 사용자가 말하면 첫 단어 놓침. 응답 끝까지 대기.
- **새 보이스 적용 안 됨**: `rm data/welcome.wav` + `rm -rf data/tts_cache` 로 캐시 무효화 후 restart.

---

### 라이브 E2E 시연 (2026-05-29 23:00 KST)
- 사용자: "향다나 … 날씨가 어때?" → STT(google) "날씨가 어때?" → Intent weather.now → MB → PS → KMA → TTS "현재 강동구 고덕동 기온은 20도예요. 하늘은 맑음이에요. 습도는 70%예요."
- 23:01 재시도: "향다나 … 내일 날씨는 어때?" → weather.tomorrow → TTS "내일 강동구 고덕동 날씨를 알려드릴게요. 하늘은 전반적으로 맑음이에요. 최저 17도, 최고 29도예요. 강수 가능성은 낮아요."
- **systemd 4-tier(PS+HIOT+MB+Jarvis) 가 마이크부터 KMA 클라우드까지 한 발화로 완전 통과**.
- 사전 트러블: USB 재인식 후 외부 측정(pw-record)에서는 Jabra 자체 노이즈 게이트로 신호가 약해 보였지만, Jarvis 내부 PvRecorder 는 정상적으로 들음 (처리 경로/chunk size 차이). 마이크 게인 0.75 → 1.5 부스트(`wpctl set-volume @DEFAULT_AUDIO_SOURCE@ 1.5`)는 외부 디버깅용이며 Jarvis 동작과 직접 관련 없을 수 있음.
