"""TTS — Google Cloud Text-to-Speech (운영 기본 엔진).

한국어 발화를 합성해 WAV로 저장하고 PipeWire(`pw-play`)로 재생한다.
(Piper 로컬 TTS는 추후 fallback으로 추가 가능 — MILESTONES M1 참고)

단독 실행:
    PYTHONPATH=src python -m jarvis.tts "안녕하세요, 저는 페퍼입니다."
    PYTHONPATH=src python -m jarvis.tts --list-voices
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import subprocess
from pathlib import Path

from jarvis import gcloud

DEFAULT_VOICE = "ko-KR-Chirp3-HD-Leda"   # 한국어 여성 Chirp3-HD (사용자 선택 2026-05-29).

# 웨이크워드 감지 직후 발화할 안내 멘트. 짧을수록 응답 latency 개선.
WELCOME_TEXT = "네, 향단이에요"
_REPO_ROOT = Path(__file__).resolve().parents[2]
WELCOME_WAV = _REPO_ROOT / "data" / "welcome.wav"

# 응답 TTS 캐시 — 동일 텍스트 재합성 회피. 시간/날씨/정형 응답이 반복되므로 효과 큼.
TTS_CACHE_DIR = _REPO_ROOT / "data" / "tts_cache"

_log = logging.getLogger("jarvis.tts")


def _cache_key(text: str, voice: str, rate: float) -> str:
    """text + voice + rate 의 해시 → 캐시 파일명. 음성 변경 시 자동 무효화."""
    h = hashlib.sha256(f"{voice}|{rate:.2f}|{text}".encode("utf-8")).hexdigest()
    return h[:16]   # 16자면 충돌 사실상 불가


def cached_wav_path(text: str, voice: str = DEFAULT_VOICE, rate: float = 1.0) -> Path:
    return TTS_CACHE_DIR / f"{_cache_key(text, voice, rate)}.wav"


def synthesize(
    text: str,
    out_path: str = "/tmp/jarvis_tts.wav",
    language: str = "ko-KR",
    voice_name: str | None = DEFAULT_VOICE,
    speaking_rate: float = 1.0,
) -> str:
    """텍스트를 합성해 LINEAR16 WAV로 저장, 경로 반환."""
    from google.cloud import texttospeech as tts

    client = tts.TextToSpeechClient(credentials=gcloud.get_credentials())
    if voice_name:
        voice = tts.VoiceSelectionParams(language_code=language, name=voice_name)
    else:
        voice = tts.VoiceSelectionParams(
            language_code=language, ssml_gender=tts.SsmlVoiceGender.FEMALE
        )
    audio_config = tts.AudioConfig(
        audio_encoding=tts.AudioEncoding.LINEAR16, speaking_rate=speaking_rate
    )
    resp = client.synthesize_speech(
        input=tts.SynthesisInput(text=text), voice=voice, audio_config=audio_config
    )
    with open(out_path, "wb") as f:
        f.write(resp.audio_content)   # LINEAR16은 WAV 헤더 포함
    return out_path


def speak(text: str, *, use_cache: bool = True, voice_name: str | None = DEFAULT_VOICE,
          speaking_rate: float = 1.0, **kw) -> str:
    """합성 후 즉시 재생. `use_cache=True` (기본) 면 같은 텍스트는 캐시 wav 재사용.

    캐시 hit → 합성 스킵, 즉시 pw-play. 첫 호출에서 합성 + 저장.
    캐시 무효화는 voice/rate 가 바뀌면 자동 (해시 키에 포함).
    """
    voice = voice_name or DEFAULT_VOICE
    if use_cache:
        path = cached_wav_path(text, voice, speaking_rate)
        if path.exists():
            _log.info("TTS 캐시 hit: %s len=%d", path.name, len(text))
            subprocess.run(["pw-play", str(path)], check=False)
            return str(path)
        TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _log.info("TTS 캐시 miss → 합성 (%s)", path.name)
        synthesize(text, out_path=str(path), voice_name=voice, speaking_rate=speaking_rate, **kw)
        subprocess.run(["pw-play", str(path)], check=False)
        return str(path)
    # use_cache=False 경로 — tmp 파일에 합성 후 즉시 재생, 캐시 안 함
    tmp = synthesize(text, voice_name=voice, speaking_rate=speaking_rate, **kw)
    subprocess.run(["pw-play", tmp], check=False)
    return tmp


def prepare_welcome_cache(force: bool = False) -> Path:
    """`WELCOME_TEXT` 를 `WELCOME_WAV` 에 1회 합성. 이미 있으면 그대로 사용.

    부팅 시 main.py 에서 호출 — 첫 wake 감지 시 합성 지연(~800ms)을 회피.
    """
    WELCOME_WAV.parent.mkdir(parents=True, exist_ok=True)
    if WELCOME_WAV.exists() and not force:
        _log.info("welcome 캐시 이미 존재: %s", WELCOME_WAV)
        return WELCOME_WAV
    _log.info("welcome 캐시 합성 시작 (%s)", WELCOME_TEXT)
    synthesize(WELCOME_TEXT, out_path=str(WELCOME_WAV))
    _log.info("welcome 캐시 저장: %s", WELCOME_WAV)
    return WELCOME_WAV


def play_welcome() -> None:
    """캐시된 welcome wav 재생. 없으면 즉시 합성 후 재생."""
    if not WELCOME_WAV.exists():
        prepare_welcome_cache()
    subprocess.run(["pw-play", str(WELCOME_WAV)], check=False)


def list_voices(language: str = "ko-KR") -> None:
    from google.cloud import texttospeech as tts

    client = tts.TextToSpeechClient(credentials=gcloud.get_credentials())
    resp = client.list_voices(language_code=language)
    for v in resp.voices:
        print(f"  {v.name:28s} {tts.SsmlVoiceGender(v.ssml_gender).name:7s} "
              f"{v.natural_sample_rate_hertz}Hz")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Google TTS 발화 테스트")
    ap.add_argument("text", nargs="?", default="안녕하세요, 저는 페퍼입니다. 무엇을 도와드릴까요?")
    ap.add_argument("--voice", default=DEFAULT_VOICE)
    ap.add_argument("--rate", type=float, default=1.0, help="speaking_rate")
    ap.add_argument("--no-play", action="store_true", help="재생 없이 wav만 생성")
    ap.add_argument("--list-voices", action="store_true", help="한국어 음성 목록")
    args = ap.parse_args(argv)

    if args.list_voices:
        list_voices()
        return 0

    print(f"[tts] 합성: voice={args.voice} rate={args.rate}\n  \"{args.text}\"")
    if args.no_play:
        print("저장:", synthesize(args.text, voice_name=args.voice, speaking_rate=args.rate))
    else:
        speak(args.text, voice_name=args.voice, speaking_rate=args.rate)
        print("[tts] 재생 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
