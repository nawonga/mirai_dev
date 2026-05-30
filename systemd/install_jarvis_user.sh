#!/usr/bin/env bash
# Mirai Space — Jarvis (사용자 세션 oauth/마이크) systemd user 설치.
# sudo 불필요. (linger 는 이미 활성화 되어있음 — 확인됨 2026-05-29)
#
# 사용:
#   bash /home/nawonga/MiraiProject/dev/systemd/install_jarvis_user.sh
#
# 제거:
#   systemctl --user disable --now jarvis.service jarvis-restart.timer
#   rm -f ~/.config/systemd/user/{jarvis.service,jarvis-restart.service,jarvis-restart.timer}
#   systemctl --user daemon-reload

set -euo pipefail

if [[ "${EUID}" -eq 0 ]]; then
  echo "ERROR: 이 스크립트는 일반 사용자(nawonga)로 실행하세요. sudo 사용 금지."
  exit 1
fi

DEV_ROOT=/home/nawonga/MiraiProject/dev
USER_UNIT_DIR="${HOME}/.config/systemd/user"

# 정본 → 심볼릭링크 대상 (모두 dev 트리에 정본)
UNITS=(
  "jarvis.service"
  "jarvis-restart.service"   # oneshot — timer 로 trigger
  "jarvis-restart.timer"     # 매일 03:00 jarvis restart (PvRecorder stream stale 회피)
)

echo "=== 1) 디렉토리/심볼릭링크 ==="
mkdir -p "${USER_UNIT_DIR}"
for unit in "${UNITS[@]}"; do
  src="${DEV_ROOT}/Jarvis/systemd/${unit}"
  dest="${USER_UNIT_DIR}/${unit}"
  ln -sf "${src}" "${dest}"
  echo "  ${dest}  ->  ${src}"
done

echo ""
echo "=== 2) daemon-reload ==="
systemctl --user daemon-reload

echo ""
echo "=== 3) enable --now ==="
# jarvis.service — 부팅 시 자동 + 즉시 기동
systemctl --user enable --now jarvis.service
# jarvis-restart.timer — 매일 03:00 fire. jarvis-restart.service 는 timer 가 trigger 만 — 직접 enable 불요.
systemctl --user enable --now jarvis-restart.timer

sleep 4

echo ""
echo "=== 4) status ==="
systemctl --user --no-pager --lines=8 status jarvis.service || true
echo "---"
systemctl --user --no-pager list-timers jarvis-restart.timer || true

echo ""
echo "=== 끝. 로그 추적: journalctl --user -u jarvis.service -f ==="
