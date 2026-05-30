#!/usr/bin/env bash
# Mirai Space — systemd unit 설치 (Dev 정본 → /etc/systemd/system 심볼릭링크)
#
# 사용 (sudo 필요):
#   sudo bash /home/nawonga/MiraiProject/dev/systemd/install.sh
#
# 동작:
# 1) 각 프로젝트 dev/systemd/*.service 를 /etc/systemd/system 으로 심볼릭링크
# 2) systemctl daemon-reload
# 3) 부팅 시 자동 기동 (enable)
# 4) 즉시 기동 (start)
# 5) 상태 출력 (status)
#
# 제거하려면:
#   sudo systemctl disable --now mirai_brain personal_service home_iot aqua-dcs-collector aqua-dcs-web
#   sudo rm /etc/systemd/system/{mirai_brain,personal_service,home_iot,aqua-dcs-collector,aqua-dcs-web}.service
#   sudo systemctl daemon-reload
#
# 주의: Aqua-DCS 만 처음 설치할 때는 venv/의존성/DB 초기화도 필요하므로,
#       이 글로벌 인스톨러보다 Aqua-DCS/scripts/install.sh 를 먼저 한 번 실행할 것.

set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: sudo 필요. 다음과 같이 실행하세요:"
  echo "  sudo bash $0"
  exit 1
fi

DEV_ROOT=/home/nawonga/MiraiProject/dev
TARGETS=(
  "${DEV_ROOT}/Personal_Service/systemd/personal_service.service"
  "${DEV_ROOT}/Home_IOT/systemd/home_iot.service"
  "${DEV_ROOT}/Mirai_brain/systemd/mirai_brain.service"
  "${DEV_ROOT}/Aqua-DCS/systemd/aqua-dcs-collector.service"
  "${DEV_ROOT}/Aqua-DCS/systemd/aqua-dcs-web.service"
)
UNITS=(personal_service home_iot mirai_brain aqua-dcs-collector aqua-dcs-web)

echo "=== 1) 심볼릭링크 생성 ==="
for src in "${TARGETS[@]}"; do
  name="$(basename "$src")"
  dest="/etc/systemd/system/${name}"
  ln -sf "$src" "$dest"
  echo "  $dest  ->  $src"
done

echo ""
echo "=== 2) daemon-reload ==="
systemctl daemon-reload

echo ""
echo "=== 3) enable (부팅 시 자동 기동) ==="
for u in "${UNITS[@]}"; do
  systemctl enable "${u}.service"
done

echo ""
echo "=== 4) start (즉시 기동) ==="
# Mirai_brain 만 start 해도 Wants 로 PS/HIOT 까지 같이 올라옴
systemctl start mirai_brain.service personal_service.service home_iot.service

sleep 3

echo ""
echo "=== 5) status ==="
for u in "${UNITS[@]}"; do
  echo "--- ${u} ---"
  systemctl --no-pager --lines=3 status "${u}.service" || true
  echo ""
done

echo "=== 끝. journalctl -u <name>.service -f 로 로그 추적 가능. ==="
