#!/usr/bin/env bash
# ============================================================
#  VITL PIANO TRANSCRIBER — STACK MANAGER
#  Quản lý toàn bộ stack: AI Core (Python) + Discord Bot (Node) + Web Panel
#  Cú pháp:
#    ./scripts/stack.sh start    — khởi động AI Core + Bot nếu chưa chạy
#    ./scripts/stack.sh stop     — dừng Bot + AI Core (giữ panel)
#    ./scripts/stack.sh restart  — stop rồi start
#    ./scripts/stack.sh status   — bảng trạng thái toàn bộ stack
#    ./scripts/stack.sh watchdog — vòng lặp tự hồi phục (chạy daemon)
# ============================================================

BOT_ROOT="/home/z/my-project/vitl-piano-transciber"
LOG_AI="$BOT_ROOT/ai_core.log"
LOG_BOT="$BOT_ROOT/bot.log"
LOG_WD="$BOT_ROOT/watchdog.log"
AI_URL="http://127.0.0.1:5000/health"
BOT_URL="http://127.0.0.1:8080/health"
PANEL_URL="http://127.0.0.1:3000/"

ts() { date "+%Y-%m-%d %H:%M:%S"; }

health() { # $1=url -> 0 nếu OK
  curl -s -m 5 -o /dev/null -w "%{http_code}" "$1" 2>/dev/null | grep -q "^2"
}

start_ai() {
  if health "$AI_URL"; then echo "[$(ts)] AI Core: đã chạy sẵn, bỏ qua."; return 0; fi
  echo "[$(ts)] Khởi động AI Core..."
  (cd "$BOT_ROOT" && python3 scripts/daemonize.py "$LOG_AI" .venv/bin/python ai_core/server.py)
  for _ in $(seq 1 30); do health "$AI_URL" && break; sleep 1; done
  health "$AI_URL" && echo "[$(ts)] AI Core: ONLINE (model nạp nền ~15s)." || echo "[$(ts)] AI Core: VẪN CHẾT sau 30s!"
}

start_bot() {
  if health "$BOT_URL"; then echo "[$(ts)] Bot: đã chạy sẵn, bỏ qua."; return 0; fi
  echo "[$(ts)] Khởi động Discord Bot..."
  (cd "$BOT_ROOT" && python3 scripts/daemonize.py "$LOG_BOT" node src/index.js)
  for _ in $(seq 1 20); do health "$BOT_URL" && break; sleep 1; done
  health "$BOT_URL" && echo "[$(ts)] Bot: ONLINE." || echo "[$(ts)] Bot: VẪN CHẾT sau 20s!"
}

stop_proc() { # $1=pattern, $2=tên
  local pids
  pids=$(pgrep -f "$1" 2>/dev/null)
  if [ -z "$pids" ]; then echo "[$(ts)] $2: không có tiến trình."; return 0; fi
  echo "[$(ts)] Dừng $2 (PID: $(echo $pids | tr '\n' ' '))..."
  pkill -TERM -f "$1" 2>/dev/null
  for _ in $(seq 1 10); do pgrep -f "$1" >/dev/null || break; sleep 1; done
  pgrep -f "$1" >/dev/null && { echo "[$(ts)] $2: không chịu chết, gửi SIGKILL"; pkill -KILL -f "$1"; }
}

cmd_start() {
  echo "===== START STACK @ $(ts) ====="
  start_ai
  start_bot
  if health "$PANEL_URL"; then echo "[$(ts)] Web Panel :3000: ONLINE."; else echo "[$(ts)] Web Panel :3000: KHÔNG PHẢN HỒI (do sandbox quản, thử mở lại preview)."; fi
  echo "===== XONG @ $(ts) ====="
}

cmd_stop() {
  echo "===== STOP STACK @ $(ts) ====="
  stop_proc "node src/index.js" "Discord Bot"
  stop_proc "ai_core/server.py" "AI Core"
  echo "===== XONG @ $(ts) ====="
}

cmd_status() {
  local ok bad
  ok="✅ ONLINE"; bad="❌ DOWN"
  echo "=============================================="
  echo " VITL PIANO STACK — TRẠNG THÁI @ $(ts)"
  echo "=============================================="
  if health "$AI_URL"; then
    local info; info=$(curl -s -m 5 "$AI_URL" | python3 -c "import json,sys;d=json.load(sys.stdin);print(f'model_loaded={d[\"model_loaded\"]} device={d[\"device\"]} ram={int(d[\"memory_usage_mb\"])}MB jobs={d[\"active_jobs\"]}/{d[\"max_concurrent_jobs\"]}')" 2>/dev/null)
    echo " AI Core :5000  $ok   ($info)"
  else
    echo " AI Core :5000  $bad"
  fi
  if health "$BOT_URL"; then
    local info; info=$(curl -s -m 5 "$BOT_URL" | python3 -c "import json,sys;d=json.load(sys.stdin);print(f'{d[\"bot\"]} uptime={d[\"uptime_seconds\"]}s guilds={d[\"guilds_count\"]} ping={d[\"ping_ms\"]}ms')" 2>/dev/null)
    echo " Bot     :8080  $ok   ($info)"
  else
    echo " Bot     :8080  $bad"
  fi
  if health "$PANEL_URL"; then
    echo " Panel   :3000  $ok"
  else
    echo " Panel   :3000  $bad"
  fi
  echo "=============================================="
}

cmd_watchdog() {
  echo "[$(ts)] Watchdog khởi động (kiểm tra mỗi 60s, log: $LOG_WD)"
  while true; do
    if ! health "$AI_URL"; then
      echo "[$(ts)] [WATCHDOG] AI Core chết -> tự khởi động lại" >> "$LOG_WD"
      start_ai >> "$LOG_WD" 2>&1
    fi
    if ! health "$BOT_URL"; then
      echo "[$(ts)] [WATCHDOG] Bot chết -> tự khởi động lại" >> "$LOG_WD"
      start_bot >> "$LOG_WD" 2>&1
    fi
    if ! health "$PANEL_URL"; then
      echo "[$(ts)] [WATCHDOG] CẢNH BÁO: Web Panel :3000 không phản hồi (cần sandbox khởi động lại dev server)" >> "$LOG_WD"
    fi
    sleep 60
  done
}

case "$1" in
  start)    cmd_start ;;
  stop)     cmd_stop ;;
  restart)  cmd_stop; sleep 2; cmd_start ;;
  status)   cmd_status ;;
  watchdog) cmd_watchdog ;;
  *) echo "Cú pháp: $0 {start|stop|restart|status|watchdog}"; exit 1 ;;
esac
