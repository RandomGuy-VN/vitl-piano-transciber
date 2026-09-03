#!/usr/bin/env bash
# ==============================================================================
# Script khởi chạy đồng thời Python AI Core và Node.js Discord Bot
# ==============================================================================
set -e

# Xác định đường dẫn Python Virtual Environment nếu có
if [ -d ".venv" ]; then
    PYTHON_BIN=".venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
else
    PYTHON_BIN="python"
fi

echo "================================================================="
echo "   🎹 KHỞI ĐỘNG VITL PIANO BOT (NODE.JS + PYTHON AI CORE) 🎹"
echo "================================================================="

# 1. Khởi chạy Python AI Core dưới nền
echo "[1/2] Đang khởi chạy Python AI Core Server (Transkun)..."
$PYTHON_BIN ai_core/server.py &
AI_PID=$!

# Bắt tín hiệu ngắt để dừng cả 2 tiến trình sạch sẽ
cleanup() {
    echo "Đang dừng các tiến trình con..."
    if [ -n "$AI_PID" ]; then
        kill "$AI_PID" 2>/dev/null || true
    fi
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Đợi AI Core sẵn sàng (tối đa 15 giây)
echo "Đang chờ Python AI Core khởi động trên cổng 5000..."
MAX_TRIES=30
COUNT=0
while [ $COUNT -lt $MAX_TRIES ]; do
    if curl -s http://127.0.0.1:5000/health >/dev/null 2>&1; then
        echo "✅ Python AI Core đã sẵn sàng!"
        break
    fi
    sleep 0.5
    COUNT=$((COUNT + 1))
done

if [ $COUNT -eq $MAX_TRIES ]; then
    echo "⚠️ Cảnh báo: AI Core chưa phản hồi sau 15 giây, tiếp tục khởi động Node.js Bot..."
fi

# 2. Khởi chạy Node.js Discord Bot
echo "[2/2] Đang khởi động Node.js Discord Bot..."
node src/index.js
