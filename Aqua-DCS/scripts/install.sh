#!/usr/bin/env bash
# Mirai Space — Aqua-DCS 설치 (venv + 의존성 + systemd 유닛 등록)
#
# 사용 (sudo 필요 — systemd 시스템 유닛 심볼릭링크 때문):
#   sudo bash /home/nawonga/MiraiProject/dev/Aqua-DCS/scripts/install.sh
#
# 동작:
#  1) venv 생성 (없으면)
#  2) pip install -r requirements.txt
#  3) data/ 디렉토리 + SQLite DB 초기화 (없으면)
#  4) systemd 유닛 심볼릭링크 (Dev 정본 → /etc/systemd/system)
#  5) daemon-reload → enable → start
#  6) status 출력
#
# 제거:
#   sudo systemctl disable --now aqua-dcs-collector aqua-dcs-web
#   sudo rm /etc/systemd/system/aqua-dcs-{collector,web}.service
#   sudo systemctl daemon-reload

set -euo pipefail

PROJECT_ROOT="/home/nawonga/MiraiProject/dev/Aqua-DCS"
RUN_USER="nawonga"

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: sudo 필요 (systemd 시스템 유닛 등록). 다음과 같이 실행:"
  echo "  sudo bash $0"
  exit 1
fi

if [[ ! -d "${PROJECT_ROOT}" ]]; then
  echo "ERROR: PROJECT_ROOT 없음: ${PROJECT_ROOT}"
  exit 1
fi

echo "=== 1) venv 생성/확인 ==="
if [[ ! -x "${PROJECT_ROOT}/venv/bin/python" ]]; then
  sudo -u "${RUN_USER}" python3 -m venv "${PROJECT_ROOT}/venv"
  echo "  venv 생성됨"
else
  echo "  venv 이미 존재"
fi

echo ""
echo "=== 2) pip install ==="
sudo -u "${RUN_USER}" "${PROJECT_ROOT}/venv/bin/pip" install --upgrade pip >/dev/null
sudo -u "${RUN_USER}" "${PROJECT_ROOT}/venv/bin/pip" install -r "${PROJECT_ROOT}/requirements.txt"

echo ""
echo "=== 3) data/ 디렉토리 + DB 초기화 ==="
mkdir -p "${PROJECT_ROOT}/data"
chown "${RUN_USER}:${RUN_USER}" "${PROJECT_ROOT}/data"
if [[ ! -f "${PROJECT_ROOT}/data/aqua.db" ]]; then
  sudo -u "${RUN_USER}" \
    PYTHONPATH="${PROJECT_ROOT}/src" \
    "${PROJECT_ROOT}/venv/bin/python" -c "from dcs.storage.sqlite import init_db; init_db()"
  echo "  DB 초기화: data/aqua.db"
else
  echo "  DB 이미 존재 (스킵)"
fi

echo ""
echo "=== 4) systemd 유닛 심볼릭링크 ==="
for unit in aqua-dcs-collector aqua-dcs-web; do
  src="${PROJECT_ROOT}/systemd/${unit}.service"
  dest="/etc/systemd/system/${unit}.service"
  ln -sf "${src}" "${dest}"
  echo "  ${dest}  ->  ${src}"
done

echo ""
echo "=== 5) daemon-reload + enable + start ==="
systemctl daemon-reload
systemctl enable aqua-dcs-collector.service aqua-dcs-web.service
systemctl restart aqua-dcs-collector.service aqua-dcs-web.service

sleep 2

echo ""
echo "=== 6) status ==="
for u in aqua-dcs-collector aqua-dcs-web; do
  echo "--- ${u} ---"
  systemctl --no-pager --lines=5 status "${u}.service" || true
  echo ""
done

echo "=== 끝. 실시간 로그: journalctl -u aqua-dcs-collector.service -f ==="
