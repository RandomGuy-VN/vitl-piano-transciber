#!/usr/bin/env python3
"""
Đóng gói dự án thành file .zip để triển khai trên VPS riêng (chạy native, không Docker).

Cách dùng:
    python3 scripts/build_release.py

Kết quả:
    release/vitl-piano-bot-vps-v<version>.zip
    (bên trong zip có 1 thư mục gốc `vitl-piano-bot/` để giải nén gọn gàng)
"""

from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELEASE_DIR = ROOT / "release"
PACKAGE_DIR_NAME = "vitl-piano-bot"

# --- Thư mục KHÔNG đưa vào gói phát hành ---
EXCLUDE_DIR_NAMES = {
    ".git", ".github", ".base44", ".agents", ".claude", ".codex",
    "node_modules", ".venv", "venv", "env",
    "__pycache__", ".pytest_cache", ".mypy_cache",
    "release", "dist", "logs", "downloads",
    ".idea", ".vscode",
}

# --- Tệp KHÔNG đưa vào gói phát hành ---
EXCLUDE_FILE_NAMES = {
    # Docker / nền tảng cloud (bản phát hành này chạy native trên Windows)
    "Dockerfile", "Dockerfile.base44", "Dockerfile.gpu",
    "docker-compose.yml", "docker-compose.base44.yml",
    "fly.toml", "render.yaml", "Procfile", "start.sh",
    # Base44 sandbox
    "AGENTS.md", ".env.base44-defaults",
    # Bí mật & cấu hình cục bộ (người dùng tự tạo .env từ .env.example)
    ".env", ".env.local",
    # Tệp VCS / IDE
    ".gitignore", ".dockerignore", ".gitattributes",
}

EXCLUDE_SUFFIXES = (
    ".pyc", ".pyo", ".log", ".mid", ".midi",
    ".mp3", ".wav", ".flac", ".m4a", ".zip", ".tmp",
)


def collect_files() -> list[Path]:
    """Liệt kê các tệp sẽ đóng gói (đã loại trừ theo quy tắc ở trên)."""
    result: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIR_NAMES]
        rel_dir = Path(dirpath).relative_to(ROOT)
        for name in filenames:
            if name in EXCLUDE_FILE_NAMES:
                continue
            if Path(name).suffix.lower() in EXCLUDE_SUFFIXES:
                continue
            result.append(rel_dir / name)
    return sorted(result)


def main() -> int:
    version = json.loads((ROOT / "package.json").read_text(encoding="utf-8")).get("version", "1.0.0")
    RELEASE_DIR.mkdir(exist_ok=True)
    zip_path = RELEASE_DIR / f"{PACKAGE_DIR_NAME}-vps-v{version}.zip"

    files = collect_files()
    if not files:
        print("Không tìm thấy tệp nào để đóng gói.", flush=True)
        return 1

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in files:
            zf.write(ROOT / rel, Path(PACKAGE_DIR_NAME) / rel)

    size_kb = zip_path.stat().st_size / 1024
    print(f"Đã tạo gói phát hành: {zip_path}")
    print(f"  - Số tệp   : {len(files)}")
    print(f"  - Dung lượng: {size_kb:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
