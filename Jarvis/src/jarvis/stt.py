"""STT Layer — faster-whisper 기반 한국어 로컬 전사.

녹음은 검증된 PipeWire 경로(`pw-record`)를 사용한다. (raw ALSA 직접 접근은
device-busy 충돌 위험이 있어 지양 — docs/audio/jabra_speak510.md 참고)

빠른 단독 실행:
    PYTHONPATH=src python -m jarvis.stt --seconds 6 --model small
"""
from __future__ import annotations

import argparse
import math
import signal
import struct
import subprocess
import sys
import time
import wave

# Whisper 권장 입력: 16kHz mono. faster-whisper가 내부에서 리샘플하지만
# 처음부터 16k mono로 녹음하면 파일이 작고 깔끔하다.
SAMPLE_RATE = 16000
CHANNELS = 1


def _beep(path: str = "/tmp/jarvis_cue.wav", freq: int = 1000, dur: float = 0.18) -> None:
    """'지금 말하세요' 신호음을 생성해 기본 sink(Jabra)로 재생한다."""
    n = int(SAMPLE_RATE * dur)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        for i in range(n):
            sample = int(0.3 * 32767 * math.sin(2 * math.pi * freq * i / SAMPLE_RATE))
            w.writeframes(struct.pack("<h", sample))
    subprocess.run(["pw-play", path], check=False)


def record(seconds: float, out_path: str = "/tmp/jarvis_stt.wav") -> str:
    """기본 입력(Jabra mic)에서 `seconds`초 녹음 후 wav 경로 반환."""
    proc = subprocess.Popen(
        ["pw-record", "--rate", str(SAMPLE_RATE), "--channels", str(CHANNELS), out_path]
    )
    try:
        time.sleep(seconds)
    finally:
        proc.send_signal(signal.SIGINT)  # pw-record가 wav 헤더를 정상 마감
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    return out_path


def transcribe(
    wav_path: str,
    model_size: str = "small",
    language: str = "ko",
    compute_type: str = "int8",
):
    """faster-whisper로 전사. (segments 리스트, info) 반환."""
    from faster_whisper import WhisperModel

    # Pi(CPU)에서는 device=cpu + int8 양자화가 속도/메모리에 유리.
    model = WhisperModel(model_size, device="cpu", compute_type=compute_type)
    segments, info = model.transcribe(wav_path, language=language, vad_filter=True)
    return list(segments), info


def _bcp47(language: str) -> str:
    """Whisper식 'ko' → Google식 'ko-KR' 변환."""
    if "-" in language:
        return language
    return {"ko": "ko-KR", "en": "en-US", "ja": "ja-JP"}.get(language, language)


def transcribe_with_fallback(
    wav_path: str,
    language: str = "ko",
    whisper_model: str = "small",
    compute_type: str = "int8",
) -> tuple[str, dict]:
    """운영 기본: Google STT 우선, 실패/빈 결과 시 Whisper로 폴백. (text, meta) 반환."""
    reason = None
    try:
        from jarvis import google_stt

        text, meta = google_stt.transcribe(wav_path, _bcp47(language))
        if text:
            return text, meta
        reason = "Google 빈 결과"
    except Exception as e:  # 네트워크/인증/쿼터 등
        reason = f"Google 실패: {type(e).__name__}: {e}"

    print(f"[STT] {reason} → Whisper fallback")
    segments, info = transcribe(wav_path, whisper_model, language, compute_type)
    text = " ".join(s.text.strip() for s in segments).strip()
    return text, {"engine": "whisper-fallback", "language": info.language}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Jarvis mic → STT 전사 테스트")
    ap.add_argument("--engine", choices=["auto", "google", "whisper"], default="auto",
                    help="auto=Google 우선·Whisper 폴백 / google / whisper")
    ap.add_argument("--seconds", type=float, default=6.0, help="녹음 길이(초)")
    ap.add_argument("--model", default="small", help="whisper 모델 크기 (tiny/base/small/medium)")
    ap.add_argument("--language", default="ko", help="언어 코드(whisper식, 예: ko)")
    ap.add_argument("--compute-type", default="int8", help="ctranslate2 compute type")
    ap.add_argument("--no-beep", action="store_true", help="시작 신호음 끄기")
    ap.add_argument("--file", help="녹음 대신 기존 wav 파일을 전사")
    args = ap.parse_args(argv)

    if args.file:
        wav = args.file
        print(f"[STT] 파일 전사: {wav} (engine={args.engine})")
    else:
        # whisper 단독일 때만 모델을 미리 로드(녹음 타이밍 정확화). google/auto는 불필요.
        if args.engine == "whisper":
            print(f"[STT] 모델 준비 중: {args.model} ...")
            from faster_whisper import WhisperModel

            WhisperModel(args.model, device="cpu", compute_type=args.compute_type)
        if not args.no_beep:
            _beep()
        print(f">>> 지금 말하세요 ({args.seconds:.0f}초) <<<", flush=True)
        wav = record(args.seconds)
        print(f"[STT] 녹음 완료, 전사 중 (engine={args.engine})...")

    t0 = time.time()
    if args.engine == "whisper":
        segments, info = transcribe(wav, args.model, args.language, args.compute_type)
        text = " ".join(s.text.strip() for s in segments).strip()
        meta = {"engine": "whisper", "language": info.language}
        for s in segments:
            print(f"  [{s.start:5.1f}–{s.end:5.1f}] {s.text.strip()}")
    elif args.engine == "google":
        from jarvis import google_stt

        text, meta = google_stt.transcribe(wav, _bcp47(args.language))
    else:
        text, meta = transcribe_with_fallback(wav, args.language, args.model, args.compute_type)
    elapsed = time.time() - t0

    print(f"\n[STT] {meta} ({elapsed:.1f}s)")
    print(f"\n=== 전사 결과 ===\n{text or '(빈 결과)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
