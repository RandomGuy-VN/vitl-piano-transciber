#!/usr/bin/env bash
# ==============================================================================
# Script khởi chạy Dev Mode — tối ưu tốc độ khởi động + live reload
# ==============================================================================
set -e

echo "================================================================="
echo "   🚀 VITL PIANO BOT — DEV MODE (PORT 3000 + LIVE RELOAD)   🚀"
echo "================================================================="

# 1. Khởi chạy Python AI Core dưới nền (không preload model → khởi động nhanh nhất)
echo "[1/2] Đang khởi chạy Python AI Core Server (Transkun)..."
python3 ai_core/server.py &
AI_PID=$!

cleanup() {
    echo "Đang dừng các tiến trình con..."
    kill "$AI_PID" 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Đợi AI Core sẵn sàng (tối đa 15 giây)
echo "Đang chờ Python AI Core khởi động trên cổng 5000..."
for i in $(seq 1 30); do
    if curl -sf http://127.0.0.1:5000/health >/dev/null 2>&1; then
        echo "✅ Python AI Core đã sẵn sàng!"
        break
    fi
    sleep 0.5
done

# 2. Khởi chạy Node.js Discord Bot với live reload (node --watch)
echo "[2/2] Đang khởi động Node.js Discord Bot (live reload)..."
exec node --watch src/index.js
