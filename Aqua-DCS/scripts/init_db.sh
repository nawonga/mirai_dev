#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$PROJECT_ROOT/src"

python - <<'PY'
from dcs.storage.sqlite import DEFAULT_DB_PATH, init_db

init_db()
print(f"Initialized DB at {DEFAULT_DB_PATH}")
PY
