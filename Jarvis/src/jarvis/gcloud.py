"""Google Cloud 공통 — 자격증명 로딩.

키는 코드에 하드코딩하지 않는다. 우선순위:
  1) 환경변수 GOOGLE_APPLICATION_CREDENTIALS
  2) 프로젝트 루트의 .env (GOOGLE_APPLICATION_CREDENTIALS=...)
  3) 기본값: <repo>/google-key-new.json
"""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]   # .../Jarvis
DEFAULT_KEY = REPO_ROOT / "google-key-new.json"


def load_env() -> None:
    """`.env`가 있으면 KEY=VALUE를 os.environ에 주입(이미 있으면 보존)."""
    env = REPO_ROOT / ".env"
    if not env.is_file():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def key_path() -> str:
    load_env()
    return os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", str(DEFAULT_KEY))


def get_credentials():
    """service_account.Credentials 반환. 키가 없으면 명확히 실패."""
    from google.oauth2 import service_account

    p = key_path()
    if not Path(p).is_file():
        raise FileNotFoundError(
            f"Google 자격증명 파일이 없습니다: {p}\n"
            ".env에 GOOGLE_APPLICATION_CREDENTIALS=<경로> 를 지정하거나 기본 키를 두세요."
        )
    return service_account.Credentials.from_service_account_file(p)
