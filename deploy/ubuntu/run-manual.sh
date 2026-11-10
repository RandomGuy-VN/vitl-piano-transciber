#!/usr/bin/env bash
#
# Chạy thử Vitl Piano Bot bằng tay (chưa cài service) để kiểm tra trước khi đưa vào vận hành.
#
# Khởi động Python AI Core, ghi log ra logs/ai_core.log, đợi AI Core sẵn sàng,
# rồi chạy Node.js Discord Bot ngay trên terminal hiện tại.
# Nhấn Ctrl+C để dừng cả Bot và AI Core.
#
# Nếu AI Core không lên được, script IN 30 DÒNG LOG CUỐI và DỪNG LẠI
# (không chạy Bot trong tình trạng hỏng) để bạn thấy ngay nguyên nhân.
#
# Dùng:
#   bash deploy/ubuntu/run-manual.sh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

AI_PORT="${AI_PORT:-5000}"
AI_STARTUP_TIMEOUT_SEC="${AI_STARTUP_TIMEOUT_SEC:-180}"
VENV_PY="$PROJECT_ROOT/.venv/bin/python"
LOG_DIR="$PROJECT_ROOT/logs"
AI_OUT="$LOG_DIR/ai_core.log"
AI_ERR="$LOG_DIR/ai_core.error.log"

if [ ! -x "$VENV_PY" ]; then
  echo "LOI: chua co .venv — hay chay: bash deploy/ubuntu/setup.sh" >&2
  exit 1
fi
if [ ! -f .env ]; then
  echo "LOI: chua co file .env — hay copy .env.example thanh .env va dien DISCORD_BOT_TOKEN." >&2
  exit 1
fi

mkdir -p "$LOG_DIR"

health_ok() {
  "$VENV_PY" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:${AI_PORT}/health', timeout=2).read()" >/dev/null 2>&1
}

# 1. Khởi động Python AI Core (ghi log ra file để chẩn đoán khi lỗi)
echo "==> Khoi dong Python AI Core (log: $AI_OUT) ..."
"$VENV_PY" ai_core/server.py >"$AI_OUT" 2>"$AI_ERR" &
AI_PID=$!

cleanup() {
  if kill -0 "$AI_PID" 2>/dev/null; then
    echo "==> Dung AI Core..."
    kill "$AI_PID" 2>/dev/null || true
    wait "$AI_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

# 2. Đợi AI Core sẵn sàng
echo "==> Doi AI Core san sang tren cong $AI_PORT (toi da ${AI_STARTUP_TIMEOUT_SEC}s) ..."
DEADLINE=$(( $(date +%s) + AI_STARTUP_TIMEOUT_SEC ))
READY=0
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  if ! kill -0 "$AI_PID" 2>/dev/null; then
    break
  fi
  if health_ok; then
    READY=1
    break
  fi
  sleep 0.5
done

if [ "$READY" -ne 1 ]; then
  echo "==> AI CORE KHONG KHOI DONG DUOC (cong $AI_PORT khong phan hoi)." >&2
  if ! kill -0 "$AI_PID" 2>/dev/null; then
    echo "    Tien trinh AI Core da thoat." >&2
  fi
  for f in "$AI_ERR" "$AI_OUT"; do
    if [ -s "$f" ]; then
      echo "--- 30 dong cuoi: $f ---" >&2
      tail -n 30 "$f" >&2
    fi
  done
  echo "==> Da dung lai (Bot khong duoc khoi dong). Xem loi truc tiep bang lenh:" >&2
  echo "    .venv/bin/python ai_core/server.py" >&2
  exit 1
fi
echo "==> AI Core da san sang."

# 3. Chạy Node.js Discord Bot
echo "==> Khoi dong Node.js Discord Bot (Ctrl+C de dung)..."
node src/index.js
