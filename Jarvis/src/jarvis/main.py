"""Jarvis 통합 루프 — Wakeword → welcome → 연속 대화 (멀티턴) → wake 복귀.

흐름 (M9 — 연속 대화):
    1. 웨이크워드 감지 (PvRecorder + Porcupine)
    2. PvRecorder 해제
    3. welcome wav 즉시 재생 ("네, 향단이에요")
    4. **연속 대화 loop**:
       - Streaming STT (single_utterance, max=`--continued-idle-seconds`)
       - 발화 인식 → Intent → 응답 TTS (캐시 활용)
       - 응답 끝나면 즉시 다시 STT 모드 (welcome 재생 X)
       - 무발화 idle timeout → loop 종료
    5. wake 대기 모드 복귀

부팅 시: tts.prepare_welcome_cache() 로 welcome wav 미리 합성.

실행:
    PYTHONPATH=src python -m jarvis.main                 # 무한 루프 (systemd)
    PYTHONPATH=src python -m jarvis.main --once
"""
from __future__ import annotations

import argparse
import logging
import time

from jarvis import google_stt, intent as intent_mod, tts, wakeword

_log = logging.getLogger("jarvis.main")


def _process_text(text: str, t_stt_end: float) -> tuple[intent_mod.Intent, str]:
    """STT 결과 → Intent → 응답 텍스트 반환 (TTS 재생 전까지)."""
    intent = intent_mod.parse(text)
    t_intent = time.time()
    print(f"[Jarvis] Intent: {intent.name} (route={intent.route}, by={intent.resolved_by}) "
          f"({t_intent - t_stt_end:.2f}s)", flush=True)
    resp = intent.reply or "무슨 말씀인지 잘 모르겠어요."
    return intent, resp


def handle_turn(porcupine, device_index: int, wake_timeout: float | None,
                stt_first_max_seconds: float, continued_idle_seconds: float) -> intent_mod.Intent | None:
    """1회 wake → 연속 대화 loop. 마지막 intent 반환 (system.stop 처리 위해).

    Args:
        stt_first_max_seconds: 첫 발화 safety cap (네트워크 hang 대비).
        continued_idle_seconds: 응답 후 다음 발화 대기 시간. 무발화 시 wake 복귀.
    """
    print("\n[Jarvis] 웨이크워드 대기 중... ('향다나')", flush=True)
    if not wakeword.detect_once(porcupine, device_index=device_index, timeout_s=wake_timeout):
        print("[Jarvis] (대기 시간 초과)", flush=True)
        return None

    t_wake = time.time()
    print("[Jarvis] ✅ '향다나' 감지", flush=True)

    # welcome 멘트 — 캐시 wav 즉시 재생
    tts.play_welcome()
    t_welcome = time.time()
    print(f"[Jarvis] welcome ({t_welcome - t_wake:.2f}s)", flush=True)

    last_intent: intent_mod.Intent | None = None
    turn_index = 0

    while True:
        is_first = turn_index == 0
        max_sec = stt_first_max_seconds if is_first else continued_idle_seconds
        label = "첫 발화" if is_first else f"연속 turn #{turn_index + 1}"
        print(f"[Jarvis] 듣는 중... ({label}, max {max_sec:.0f}s)", flush=True)

        t_listen_start = time.time()
        text, meta = google_stt.transcribe_streaming(device_index, max_seconds=max_sec)
        t_stt_end = time.time()
        print(f"[Jarvis] STT({meta.get('engine')}): {text!r}  "
              f"({t_stt_end - t_listen_start:.2f}s, elapsed={meta.get('elapsed_s')})", flush=True)

        if not text:
            # 빈 결과 처리: 첫 발화면 사과 멘트, 연속 모드면 조용히 wake 복귀
            if is_first:
                tts.speak("죄송해요, 잘 못 들었어요. 다시 말씀해 주세요.")
            else:
                print(f"[Jarvis] (연속 대화 idle {continued_idle_seconds:.0f}s 무발화 — wake 복귀)",
                      flush=True)
            break

        intent, resp = _process_text(text, t_stt_end)
        print(f"[Jarvis] 응답: {resp!r}", flush=True)
        t_tts_start = time.time()
        tts.speak(resp)
        t_tts_end = time.time()
        print(f"[Jarvis] 응답 완료 (TTS {t_tts_end - t_tts_start:.2f}s, "
              f"turn 시작→발화 끝 {t_tts_end - t_listen_start:.2f}s)", flush=True)

        last_intent = intent
        turn_index += 1

        # system.sleep: 잘못된 응답 후 사용자가 wake 복귀 요청 ("너 아니야", "들어가" 등)
        # system.stop: 진짜 종료 의도 (systemd 가 다시 살림 — 의미적 종료)
        if intent.name in ("system.sleep", "system.stop"):
            reason = "wake 복귀 요청" if intent.name == "system.sleep" else "종료 의도"
            print(f"[Jarvis] {reason} — 연속 대화 종료", flush=True)
            break

    t_total = time.time()
    print(f"[Jarvis] === 대화 세션 종료 ({turn_index} turn, wake→끝 {t_total - t_wake:.2f}s) ===",
          flush=True)
    return last_intent


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    ap = argparse.ArgumentParser(
        description="Jarvis 통합 루프 (Wakeword→welcome→연속 대화→wake 복귀)")
    ap.add_argument("--device", type=int, default=None, help="마이크 장치 인덱스(기본=자동 탐색)")
    ap.add_argument("--once", action="store_true", help="한 세션 처리 후 종료")
    ap.add_argument("--wake-timeout", type=float, default=None, help="웨이크워드 대기 제한(초)")
    ap.add_argument("--stt-max-seconds", type=float, default=12.0,
                    help="첫 발화 streaming STT safety cap (네트워크 hang 대비)")
    ap.add_argument("--continued-idle-seconds", type=float, default=10.0,
                    help="응답 후 다음 발화 대기 시간. 무발화 시 wake 복귀.")
    ap.add_argument("--skip-welcome-cache", action="store_true",
                    help="부팅 시 welcome wav 미리 합성 생략")
    ap.add_argument("--wake-sensitivity", type=float, default=0.85,
                    help="Porcupine 웨이크워드 감지 민감도 (0~1). 한국어 '향다나'는 0.85 권장.")
    args = ap.parse_args(argv)

    # 부팅 시 welcome wav 캐시 준비 (첫 wake 무지연)
    if not args.skip_welcome_cache:
        try:
            tts.prepare_welcome_cache()
        except Exception as e:
            print(f"[Jarvis] welcome 캐시 준비 실패 (무시): {e}", flush=True)

    device = args.device if args.device is not None else wakeword.find_mic_device()
    print(f"[Jarvis] 시작. device={device} sensitivity={args.wake_sensitivity} "
          f"continued_idle={args.continued_idle_seconds:.0f}s", flush=True)
    porcupine = wakeword.create_porcupine(sensitivity=args.wake_sensitivity)
    try:
        while True:
            intent = handle_turn(
                porcupine, device,
                wake_timeout=args.wake_timeout,
                stt_first_max_seconds=args.stt_max_seconds,
                continued_idle_seconds=args.continued_idle_seconds,
            )
            if args.once:
                break
            if intent is not None and intent.name == "system.stop":
                print("[Jarvis] 종료 의도 감지 — 루프 종료", flush=True)
                break
    except KeyboardInterrupt:
        print("\n[Jarvis] 종료", flush=True)
    finally:
        porcupine.delete()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
