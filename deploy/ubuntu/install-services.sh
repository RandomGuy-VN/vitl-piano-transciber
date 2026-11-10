#!/usr/bin/env bash
#
# Cài Vitl Piano Bot thành systemd service (tự khởi động cùng máy, tự chạy lại khi lỗi).
#
# Tạo 2 service:
#   vitl-piano-ai.service   : Python AI Core  (ai_core/server.py)
#   vitl-piano-bot.service  : Node.js Bot     (src/index.js), phụ thuộc vitl-piano-ai
#
# Dùng:
#   sudo bash deploy/ubuntu/install-services.sh

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "LOI: hay chay bang sudo: sudo bash deploy/ubuntu/install-services.sh" >&2
  exit 1
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_PY="$PROJECT_ROOT/.venv/bin/python"
LOG_DIR="$PROJECT_ROOT/logs"
AI_PORT="${AI_PORT:-5000}"

# Service chạy bằng user thường gọi sudo (không chạy bot bằng root)
RUN_USER="${SUDO_USER:-root}"
if [ "$RUN_USER" = "root" ]; then
  echo "CANH BAO: khong xac dinh duoc user thuong (SUDO_USER rong) — service se chay bang root." >&2
fi

NODE_BIN="$(command -v node || true)"

if [ ! -x "$VENV_PY" ]; then
  echo "LOI: chua co .venv — hay chay: bash deploy/ubuntu/setup.sh" >&2
  exit 1
fi
if [ -z "$NODE_BIN" ]; then
  echo "LOI: khong tim thay 'node' trong PATH." >&2
  exit 1
fi

mkdir -p "$LOG_DIR"
chown -R "$RUN_USER":"$RUN_USER" "$LOG_DIR" 2>/dev/null || true

AI_UNIT="/etc/systemd/system/vitl-piano-ai.service"
BOT_UNIT="/etc/systemd/system/vitl-piano-bot.service"

# --- Service 1: Python AI Core ---
echo "==> Tao $AI_UNIT ..."
cat > "$AI_UNIT" <<EOF
[Unit]
Description=Vitl Piano - Python AI Core (Transkun)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$PROJECT_ROOT
Environment=PYTHONUNBUFFERED=1
ExecStart=$VENV_PY ai_core/server.py
Restart=always
RestartSec=5
StandardOutput=append:$LOG_DIR/ai_core.log
StandardError=append:$LOG_DIR/ai_core.error.log

[Install]
WantedBy=multi-user.target
EOF

# --- Service 2: Node.js Discord Bot ---
echo "==> Tao $BOT_UNIT ..."
cat > "$BOT_UNIT" <<EOF
[Unit]
Description=Vitl Piano - Discord Bot (Node.js)
After=network-online.target vitl-piano-ai.service
Wants=network-online.target
Requires=vitl-piano-ai.service

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$PROJECT_ROOT
Environment=NODE_ENV=production
ExecStart=$NODE_BIN src/index.js
Restart=always
RestartSec=5
StandardOutput=append:$LOG_DIR/bot.log
StandardError=append:$LOG_DIR/bot.error.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

# --- Khởi động AI Core và đợi nó thật sự lắng nghe ---
echo "==> Khoi dong vitl-piano-ai ..."
systemctl enable --now vitl-piano-ai.service

echo "==> Doi AI Core san sang tren cong $AI_PORT ..."
READY=0
for _ in $(seq 1 180); do
  if "$VENV_PY" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:${AI_PORT}/health', timeout=2).read()" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 1
done

if [ "$READY" -ne 1 ]; then
  echo "==> CANH BAO: AI Core khong phan hoi tren cong $AI_PORT -> Bot se bao 'ECONNREFUSED'." >&2
  echo "--- 30 dong cuoi: $LOG_DIR/ai_core.error.log ---" >&2
  tail -n 30 "$LOG_DIR/ai_core.error.log" 2>/dev/null >&2 || true
  echo "--- 30 dong cuoi: $LOG_DIR/ai_core.log ---" >&2
  tail -n 30 "$LOG_DIR/ai_core.log" 2>/dev/null >&2 || true
  echo "Da dung lai. Sua loi roi chay lai script nay." >&2
  exit 1
fi
echo "==> AI Core da san sang."

echo "==> Khoi dong vitl-piano-bot ..."
systemctl enable --now vitl-piano-bot.service

sleep 2
systemctl --no-pager --lines=0 status vitl-piano-ai.service vitl-piano-bot.service || true

echo "==> Hoan tat. Xem log tai: $LOG_DIR"
echo "    Theo doi truc tiep: journalctl -u vitl-piano-bot -f"
