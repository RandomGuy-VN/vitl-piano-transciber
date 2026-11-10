#!/usr/bin/env bash
#
# Gỡ Vitl Piano Bot khỏi systemd (giữ nguyên mã nguồn, .venv và logs).
#
# Dùng:
#   sudo bash deploy/ubuntu/uninstall-services.sh

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "LOI: hay chay bang sudo: sudo bash deploy/ubuntu/uninstall-services.sh" >&2
  exit 1
fi

for svc in vitl-piano-bot vitl-piano-ai; do
  echo "==> Go service: $svc"
  systemctl disable --now "$svc.service" 2>/dev/null || true
  rm -f "/etc/systemd/system/$svc.service"
done

systemctl daemon-reload
systemctl reset-failed 2>/dev/null || true

echo "==> Da go service. Ma nguon, .venv va logs van giu nguyen."
