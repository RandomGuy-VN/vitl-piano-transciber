#!/usr/bin/env bash
#
# Cài đặt môi trường Vitl Piano Bot trên Ubuntu Server (chạy native, KHÔNG dùng Docker).
#
# Dùng:
#   bash deploy/ubuntu/setup.sh            # PyTorch bản CPU
#   bash deploy/ubuntu/setup.sh --cuda     # PyTorch bản CUDA (VPS có GPU NVIDIA)
#
# KHÔNG cần sudo: mọi thứ được cài trong thư mục dự án (.venv, node_modules).
# Các gói hệ thống (python3.12, nodejs, ffmpeg) cài riêng — xem docs/UBUNTU-VPS.md.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

TORCH_VARIANT="cpu"
if [ "${1:-}" = "--cuda" ]; then
  TORCH_VARIANT="cuda"
fi

echo "==> Thu muc du an: $PROJECT_ROOT"

# ------------------------------------------------------------------
# 1. Dò Python 3.10+ (ưu tiên 3.12)
# ------------------------------------------------------------------
PY=""
for candidate in python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
      PY="$(command -v "$candidate")"
      break
    fi
  fi
done

if [ -z "$PY" ]; then
  echo "LOI: khong tim thay Python 3.10+." >&2
  echo "     Cai bang: sudo apt install -y python3.12 python3.12-venv" >&2
  exit 1
fi
echo "==> Dung Python: $PY ($("$PY" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))'))"

# ------------------------------------------------------------------
# 2. Kiểm tra công cụ hệ thống
# ------------------------------------------------------------------
MISSING=0
for tool in node npm ffmpeg ffprobe; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "LOI: chua co '$tool' trong PATH." >&2
    MISSING=1
  fi
done
if [ "$MISSING" -eq 1 ]; then
  cat >&2 <<'EOF'

Cai dat cac goi con thieu:
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt install -y nodejs ffmpeg
roi chay lai script nay.
EOF
  exit 1
fi
echo "==> Node  : $(node --version)"
echo "==> FFmpeg: $(ffmpeg -version | head -n 1 | cut -d' ' -f3)"

# ------------------------------------------------------------------
# 3. Tạo virtualenv .venv
# ------------------------------------------------------------------
if [ -d .venv ] && [ ! -x .venv/bin/python ]; then
  echo "==> Phat hien .venv bi hong (thieu bin/python) -> xoa va tao lai..."
  rm -rf .venv
fi

if [ ! -x .venv/bin/python ]; then
  echo "==> Tao virtualenv .venv ..."
  if ! "$PY" -m venv .venv; then
    echo "LOI: tao virtualenv that bai. Tren Ubuntu can goi: sudo apt install -y python3-venv" >&2
    exit 1
  fi
fi

VENV_PY="$PROJECT_ROOT/.venv/bin/python"
echo "==> Virtualenv: $VENV_PY"

# ------------------------------------------------------------------
# 4. Cài PyTorch + requirements.txt
# ------------------------------------------------------------------
echo "==> Nang cap pip ..."
"$VENV_PY" -m pip install --upgrade pip

echo "==> Cai PyTorch ($TORCH_VARIANT) ... (co the mat vai phut)"
if [ "$TORCH_VARIANT" = "cuda" ]; then
  "$VENV_PY" -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
else
  "$VENV_PY" -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

echo "==> Cai requirements.txt ..."
"$VENV_PY" -m pip install -r requirements.txt

# ------------------------------------------------------------------
# 5. Cài dependencies Node.js
# ------------------------------------------------------------------
echo "==> Cai dependencies Node.js ..."
if [ -f package-lock.json ]; then
  npm ci --omit=dev
else
  npm install --omit=dev
fi

# ------------------------------------------------------------------
# 6. Tạo file .env nếu chưa có
# ------------------------------------------------------------------
if [ ! -f .env ]; then
  cp .env.example .env
  echo "==> Da tao file .env tu .env.example -> MO FILE .env VA DIEN DISCORD_BOT_TOKEN!"
else
  echo "==> File .env da ton tai, bo qua."
fi

echo "==> Cai dat hoan tat!"
echo "    Buoc tiep theo: bash deploy/ubuntu/run-manual.sh"
