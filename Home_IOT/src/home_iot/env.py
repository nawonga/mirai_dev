"""공용 .env 로더 (Home_IOT 루트의 .env). 시크릿/토큰은 코드 하드코딩 금지."""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]   # .../Home_IOT


def load_env() -> None:
    env = REPO_ROOT / ".env"
    if not env.is_file():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
