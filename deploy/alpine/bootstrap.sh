#!/bin/sh
#
# Tải mã nguồn Vitl Piano Bot về máy Alpine rồi cài đặt (Docker).
#
# Dùng 1 dòng (không cần tải file trước, không cần unzip):
#   curl -fsSL https://raw.githubusercontent.com/RandomGuy-VN/vitl-piano-transciber/port-performance-optimization/deploy/alpine/bootstrap.sh | sudo sh
#
# Chạy lại cùng lệnh để CẬP NHẬT mã nguồn (file .env được giữ nguyên).
#
# Tuỳ chọn (đặt trước lệnh sh):
#   VITL_BRANCH=main          # nhánh muốn lấy (mặc định: port-performance-optimization)
#   VITL_DIR=/opt/vitl-piano-bot   # thư mục cài đặt

set -eu

if [ "$(id -u)" -ne 0 ]; then
  echo "LOI: hay chay bang sudo." >&2
  exit 1
fi

BRANCH="${VITL_BRANCH:-port-performance-optimization}"
DIR="${VITL_DIR:-/opt/vitl-piano-bot}"
REPO="${VITL_REPO:-https://github.com/RandomGuy-VN/vitl-piano-transciber.git}"

# ------------------------------------------------------------------
# 1. Gói cần thiết
# ------------------------------------------------------------------
if ! command -v git >/dev/null 2>&1 || ! command -v curl >/dev/null 2>&1; then
  echo "==> Cai git + curl ..."
  apk update
  apk add --no-cache git curl
fi

# ------------------------------------------------------------------
# 2. Lấy / cập nhật mã nguồn
# ------------------------------------------------------------------
if [ -d "$DIR/.git" ]; then
  echo "==> Cap nhat ma nguon trong $DIR (nhanh $BRANCH) ..."
  cd "$DIR"
  git fetch origin "$BRANCH"
  git checkout "$BRANCH"
  git reset --hard "origin/$BRANCH"
else
  echo "==> Clone ma nguon ve $DIR (nhanh $BRANCH) ..."
  mkdir -p "$(dirname "$DIR")"
  rm -rf "$DIR"
  git clone --branch "$BRANCH" --depth 1 "$REPO" "$DIR"
  cd "$DIR"
fi

# ------------------------------------------------------------------
# 3. Cài đặt (script này tự cài Docker, kiểm tra .env, build container)
# ------------------------------------------------------------------
exec sh deploy/alpine/setup.sh
