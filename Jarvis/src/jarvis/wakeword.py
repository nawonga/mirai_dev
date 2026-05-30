"""Wakeword Layer — Porcupine 한국어 웨이크워드 감지.

키워드: "향다나" (Hyangdana_ko_raspberry-pi_v4_0_0.ppn)
한국어 키워드이므로 한국어 모델 파라미터(`porcupine_params_ko.pv`)가 필요하다.

액세스 키는 보안상 코드에 하드코딩하지 않고 환경변수 `PV_ACCESS_KEY`
또는 프로젝트 루트의 `.env`(gitignore됨)에서 읽는다.

단독 실행:
    PYTHONPATH=src python -m jarvis.wakeword            # 기본 장치로 감지 루프
    PYTHONPATH=src python -m jarvis.wakeword --list     # 입력 장치 목록
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]   # .../Jarvis
DEFAULT_KEYWORD = REPO_ROOT / "Hyangdana_ko_raspberry-pi_v4_0_0.ppn"
DEFAULT_MODEL = REPO_ROOT / "data" / "models" / "porcupine" / "porcupine_params_ko.pv"


def _load_env() -> None:
    """`.env`가 있으면 단순 KEY=VALUE 파싱하여 os.environ에 주입(이미 있으면 보존)."""
    env = REPO_ROOT / ".env"
    if not env.is_file():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_access_key() -> str:
    _load_env()
    key = os.environ.get("PV_ACCESS_KEY")
    if not key:
        sys.exit(
            "PV_ACCESS_KEY가 없습니다. console.picovoice.ai의 AccessKey를\n"
            f"  {REPO_ROOT}/.env  에  PV_ACCESS_KEY=<키>  형태로 넣거나\n"
            "  export PV_ACCESS_KEY=<키>  로 설정하세요."
        )
    return key


def find_mic_device() -> int:
    """모니터(스피커 루프백)가 아닌 첫 입력 장치 인덱스를 찾는다. ([0]=Monitor 회피)"""
    from pvrecorder import PvRecorder

    for i, d in enumerate(PvRecorder.get_available_devices()):
        if "monitor" not in d.lower():
            return i
    return -1


def create_porcupine(
    access_key: str | None = None,
    keyword_path: str = str(DEFAULT_KEYWORD),
    model_path: str = str(DEFAULT_MODEL),
    sensitivity: float = 0.5,
):
    """Porcupine 인스턴스 생성(루프 전체에서 재사용). 키는 .env에서 자동 로드."""
    import pvporcupine

    return pvporcupine.create(
        access_key=access_key or get_access_key(),
        model_path=model_path,
        keyword_paths=[keyword_path],
        sensitivities=[sensitivity],
    )


def detect_once(porcupine, device_index: int = -1, timeout_s: float | None = None) -> bool:
    """PvRecorder를 열어 웨이크워드 1회 감지. 감지/타임아웃 시 recorder를 해제(마이크 반납).

    감지=True, 타임아웃=False. 마이크를 반납하므로 직후 STT(pw-record) 사용 가능.
    """
    from pvrecorder import PvRecorder

    rec = PvRecorder(frame_length=porcupine.frame_length, device_index=device_index)
    start = time.monotonic()
    rec.start()
    try:
        while True:
            if porcupine.process(rec.read()) >= 0:
                return True
            if timeout_s is not None and (time.monotonic() - start) > timeout_s:
                return False
    finally:
        rec.stop()
        rec.delete()   # ★ 마이크 반납 — STT가 같은 장치를 열 수 있게 함


def listen(
    access_key: str,
    keyword_path: str = str(DEFAULT_KEYWORD),
    model_path: str = str(DEFAULT_MODEL),
    sensitivity: float = 0.5,
    device_index: int = -1,
    on_detect=None,
    once: bool = False,
    timeout_s: float | None = None,
) -> int:
    """웨이크워드 감지 루프. 감지 시 on_detect() 호출(없으면 확인음).

    once=True면 첫 감지 후 종료, timeout_s 지정 시 해당 시간 후 자동 종료.
    감지 횟수를 반환한다.
    """
    import pvporcupine
    from pvrecorder import PvRecorder

    porcupine = pvporcupine.create(
        access_key=access_key,
        model_path=model_path,
        keyword_paths=[keyword_path],
        sensitivities=[sensitivity],
    )
    recorder = PvRecorder(frame_length=porcupine.frame_length, device_index=device_index)
    print(f"[WAKE] 대기 중... (sample_rate={porcupine.sample_rate}, "
          f"frame={porcupine.frame_length}, sensitivity={sensitivity}, "
          f"device={recorder.selected_device})")
    print("       '향다나' 라고 말해보세요." + (f" ({timeout_s:.0f}초 후 자동 종료)" if timeout_s else " (Ctrl+C 종료)"))
    count = 0
    start = time.monotonic()
    recorder.start()
    try:
        while True:
            pcm = recorder.read()
            if porcupine.process(pcm) >= 0:
                count += 1
                print(f"\a[WAKE] ✅ '향다나' 감지! (#{count})", flush=True)
                if on_detect:
                    on_detect()
                else:
                    try:
                        from jarvis.stt import _beep
                        _beep(freq=1200, dur=0.15)
                    except Exception:
                        pass
                if once:
                    break
            if timeout_s is not None and (time.monotonic() - start) > timeout_s:
                print(f"[WAKE] {timeout_s:.0f}초 경과 — 종료 (감지 {count}회)")
                break
    except KeyboardInterrupt:
        print("\n[WAKE] 종료")
    finally:
        recorder.stop()
        recorder.delete()
        porcupine.delete()
    return count


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Porcupine 한국어 웨이크워드 감지")
    ap.add_argument("--list", action="store_true", help="입력 장치 목록 출력")
    ap.add_argument("--device", type=int, default=-1, help="입력 장치 인덱스(-1=기본)")
    ap.add_argument("--keyword", default=str(DEFAULT_KEYWORD), help=".ppn 경로")
    ap.add_argument("--model", default=str(DEFAULT_MODEL), help="ko 모델 파라미터 경로")
    ap.add_argument("--sensitivity", type=float, default=0.5, help="0~1, 높을수록 민감")
    ap.add_argument("--once", action="store_true", help="첫 감지 후 종료")
    ap.add_argument("--timeout", type=float, default=None, help="N초 후 자동 종료")
    args = ap.parse_args(argv)

    if args.list:
        from pvrecorder import PvRecorder
        for i, d in enumerate(PvRecorder.get_available_devices()):
            print(f"  [{i}] {d}")
        return 0

    for p in (args.keyword, args.model):
        if not Path(p).is_file():
            sys.exit(f"파일 없음: {p}")

    listen(
        access_key=get_access_key(),
        keyword_path=args.keyword,
        model_path=args.model,
        sensitivity=args.sensitivity,
        device_index=args.device,
        once=args.once,
        timeout_s=args.timeout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
