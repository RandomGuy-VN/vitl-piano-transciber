#!/bin/sh
#
# Cài và chạy Vitl Piano Bot trên Alpine Linux bằng Docker.
#
# VÌ SAO PHẢI DÙNG DOCKER:
#   PyTorch chỉ phát hành wheel cho glibc (manylinux) — không có bản musl — và kho
#   Alpine cũng không có gói `py3-torch`. Vì vậy KHÔNG thể `pip install torch` native
#   trên Alpine. Container dùng image python:3.12-slim (Debian/glibc) nên chạy bình thường.
#
# Dùng:
#   sudo sh deploy/alpine/setup.sh

set -eu

if [ "$(id -u)" -ne 0 ]; then
  echo "LOI: hay chay bang sudo: sudo sh deploy/alpine/setup.sh" >&2
  exit 1
fi

PROJECT_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$PROJECT_ROOT"

echo "==> Thu muc du an: $PROJECT_ROOT"

# ------------------------------------------------------------------
# 1. Cài Docker + Compose plugin
# ------------------------------------------------------------------
if command -v docker >/dev/null 2>&1; then
  echo "==> Docker da co san."
else
  echo "==> Cai Docker + Compose plugin ..."
  apk update
  apk add --no-cache docker docker-cli docker-cli-compose docker-cli-buildx
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "==> Cai them Compose plugin ..."
  apk add --no-cache docker-cli-compose
fi

# ------------------------------------------------------------------
# 2. Bật Docker daemon (OpenRC)
# ------------------------------------------------------------------
if command -v rc-update >/dev/null 2>&1; then
  rc-update add docker default >/dev/null 2>&1 || true
  service docker start >/dev/null 2>&1 || true
else
  echo "CANH BAO: khong thay rc-update (khong phai OpenRC) — hay tu khoi dong docker daemon." >&2
fi

echo "==> Doi docker daemon san sang ..."
i=0
while [ "$i" -lt 60 ]; do
  if docker info >/dev/null 2>&1; then
    break
  fi
  i=$((i + 1))
  sleep 1
done
if ! docker info >/dev/null 2>&1; then
  echo "LOI: docker daemon chua san sang. Thu chay: service docker start" >&2
  exit 1
fi

# ------------------------------------------------------------------
# 3. Kiểm tra .env
# ------------------------------------------------------------------
if [ ! -f .env ]; then
  cp .env.example .env
  echo "==> Da tao file .env tu .env.example."
  echo "    MO FILE .env, dien DISCORD_BOT_TOKEN roi chay lai script nay."
  exit 1
fi

if ! grep -q '^DISCORD_BOT_TOKEN=.' .env || grep -q '^DISCORD_BOT_TOKEN=your_discord_bot_token_here' .env; then
  echo "LOI: DISCORD_BOT_TOKEN trong .env chua duoc dien." >&2
  exit 1
fi

# ------------------------------------------------------------------
# 4. Build + khởi động container
# ------------------------------------------------------------------
echo "==> Build image va khoi dong container (lan dau co the mat vai phut) ..."
docker compose up -d --build

# ------------------------------------------------------------------
# 5. Đợi AI Core sẵn sàng
#    (web health server chỉ bật khi BASE44_PREVIEW_MODE=1 nên không dùng /health ngoài)
# ------------------------------------------------------------------
echo "==> Doi AI Core san sang ..."
READY=0
i=0
while [ "$i" -lt 300 ]; do
  if docker compose exec -T vitl-piano-bot python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=2).read()" >/dev/null 2>&1; then
    READY=1
    break
  fi
  i=$((i + 1))
  sleep 1
done

if [ "$READY" -ne 1 ]; then
  echo "==> CANH BAO: AI Core khong phan hoi trong container." >&2
  docker compose logs --tail 60 >&2 || true
  exit 1
fi

echo "==> AI Core da san sang."
docker compose ps
echo "==> Hoan tat. Theo doi log: docker compose logs -f"
