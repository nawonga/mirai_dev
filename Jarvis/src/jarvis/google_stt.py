"""STT — Google Cloud Speech-to-Text (운영 기본 엔진).

두 가지 모드:
- `transcribe(wav_path)` — 동기 recognize (기존; wav 한 번에 전송)
- `transcribe_streaming(device_index)` — **streaming + single_utterance**
  PvRecorder 32ms chunk 를 동시에 보내며 Google 이 발화 끝을 자동 감지 → 발화
  종료 ~300ms 후 final 결과. 6초 고정 녹음 제거, 사용자 발화 길이에 자동 맞춤.

단독 실행:
    PYTHONPATH=src python -m jarvis.google_stt --seconds 6          # 마이크 녹음 후 전사
    PYTHONPATH=src python -m jarvis.google_stt --file some.wav
    PYTHONPATH=src python -m jarvis.google_stt --streaming           # 신규: streaming 모드
"""
from __future__ import annotations

import argparse
import logging
import struct
import time
import wave

from jarvis import gcloud

_log = logging.getLogger("jarvis.google_stt")

# Streaming STT 기본값
STREAM_SAMPLE_RATE = 16000
STREAM_FRAME_LENGTH = 512    # PvRecorder 프레임 (≈ 32ms @ 16kHz)
STREAM_DEFAULT_TIMEOUT = 10.0  # safety cap


def transcribe(wav_path: str, language: str = "ko-KR") -> tuple[str, dict]:
    """Google STT로 전사. (text, meta) 반환."""
    from google.cloud import speech

    with wave.open(wav_path, "rb") as w:
        rate = w.getframerate()
        channels = w.getnchannels()
        content = w.readframes(w.getnframes())

    client = speech.SpeechClient(credentials=gcloud.get_credentials())
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=rate,
        audio_channel_count=channels,
        language_code=language,
        enable_automatic_punctuation=True,
    )
    audio = speech.RecognitionAudio(content=content)
    resp = client.recognize(config=config, audio=audio)

    text = " ".join(r.alternatives[0].transcript for r in resp.results).strip()
    conf = max((r.alternatives[0].confidence for r in resp.results), default=0.0)
    return text, {"engine": "google", "language": language, "confidence": conf}


def transcribe_streaming(
    device_index: int,
    language: str = "ko-KR",
    max_seconds: float = STREAM_DEFAULT_TIMEOUT,
) -> tuple[str, dict]:
    """PvRecorder chunk 를 Google streaming_recognize 에 실시간 yield.

    `single_utterance=True` 로 Google 이 발화 끝(end-of-speech)을 자동 감지하면 즉시 종료.
    `max_seconds` 는 안전망 (네트워크 hang 등).

    Returns:
        (text, meta) — meta 에 `engine`, `elapsed_s`, `interim_count`, `end_event` 포함.
    """
    from google.cloud import speech
    from pvrecorder import PvRecorder

    client = speech.SpeechClient(credentials=gcloud.get_credentials())
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=STREAM_SAMPLE_RATE,
        audio_channel_count=1,
        language_code=language,
        enable_automatic_punctuation=True,
    )
    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        single_utterance=True,   # 발화 끝 자동 감지
        interim_results=True,    # 진행 중 결과 (디버그용 — final 만 텍스트로 사용)
    )

    recorder = PvRecorder(frame_length=STREAM_FRAME_LENGTH, device_index=device_index)
    recorder.start()

    # state: generator 가 종료 신호를 받기 위한 플래그
    state = {"stop": False, "t0": time.time()}

    def requests():
        while not state["stop"]:
            if time.time() - state["t0"] > max_seconds:
                _log.warning("streaming STT max_seconds(%s) 초과 — 중단", max_seconds)
                return
            try:
                frame = recorder.read()
            except Exception as e:
                _log.warning("PvRecorder read 실패: %s", e)
                return
            chunk = struct.pack(f"{len(frame)}h", *frame)
            yield speech.StreamingRecognizeRequest(audio_content=chunk)

    final_text = ""
    interim_count = 0
    end_event = False
    try:
        responses = client.streaming_recognize(streaming_config, requests())
        for response in responses:
            # Google 이 발화 끝 감지 시 신호. 보통 직후 final 결과 도착.
            if response.speech_event_type == \
                    speech.StreamingRecognizeResponse.SpeechEventType.END_OF_SINGLE_UTTERANCE:
                end_event = True
            for result in response.results:
                if result.is_final:
                    final_text = result.alternatives[0].transcript.strip()
                    state["stop"] = True
                    break
                else:
                    interim_count += 1
            if state["stop"]:
                break
    finally:
        state["stop"] = True
        try:
            recorder.stop()
        except Exception:
            pass
        try:
            recorder.delete()
        except Exception:
            pass

    elapsed = time.time() - state["t0"]
    meta = {
        "engine": "google-streaming",
        "language": language,
        "elapsed_s": round(elapsed, 2),
        "interim_count": interim_count,
        "end_event": end_event,
    }
    return final_text, meta


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Google STT 전사 테스트")
    ap.add_argument("--seconds", type=float, default=6.0)
    ap.add_argument("--language", default="ko-KR")
    ap.add_argument("--file", help="녹음 대신 기존 wav 전사")
    ap.add_argument("--no-beep", action="store_true")
    ap.add_argument("--streaming", action="store_true",
                    help="신규: streaming + single_utterance 모드 (마이크 직접 사용)")
    ap.add_argument("--device", type=int, default=None,
                    help="streaming 모드의 PvRecorder device index")
    ap.add_argument("--max-seconds", type=float, default=STREAM_DEFAULT_TIMEOUT,
                    help="streaming 모드 safety cap")
    args = ap.parse_args(argv)

    if args.streaming:
        from jarvis import wakeword
        dev = args.device if args.device is not None else wakeword.find_mic_device()
        print(f">>> [streaming] device={dev} — 말씀하세요 (자동 종료) <<<", flush=True)
        text, meta = transcribe_streaming(dev, args.language, args.max_seconds)
        print(f"[google-stt] {meta}")
        print(f"\n=== 전사 결과 ===\n{text or '(빈 결과)'}")
        return 0

    if args.file:
        wav = args.file
    else:
        from jarvis.stt import record, _beep
        if not args.no_beep:
            _beep()
        print(f">>> 지금 말하세요 ({args.seconds:.0f}초) <<<", flush=True)
        wav = record(args.seconds)
        print("[google-stt] 녹음 완료, 전사 중...")

    text, meta = transcribe(wav, args.language)
    print(f"[google-stt] engine={meta['engine']} conf={meta['confidence']:.2f}")
    print(f"\n=== 전사 결과 ===\n{text or '(빈 결과)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
