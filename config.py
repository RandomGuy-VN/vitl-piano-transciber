"""
Module quản lý cấu hình hệ thống và biến môi trường cho Vitl Piano Discord Bot.
Tối ưu hóa cho môi trường triển khai Cloud (Docker, Railway, Render, Fly.io, VPS).
"""

import os
import shutil
import logging
from typing import Tuple, Dict, List
from dotenv import load_dotenv

# Tải các biến môi trường từ file .env
load_dotenv()

def _get_str_env(key: str, default: str = "") -> str:
    val = os.getenv(key)
    if val is None or not val.strip():
        return default
    return val.strip()


def _get_int_env(key: str, default: int) -> int:
    val = os.getenv(key)
    if val is None or not val.strip():
        return default
    try:
        return int(val.strip())
    except ValueError:
        return default


def _get_bool_env(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None or not val.strip():
        return default
    return val.strip().lower() in ("true", "1", "yes")


# --- Discord Bot Settings ---
DISCORD_BOT_TOKEN: str = _get_str_env("DISCORD_BOT_TOKEN")
GUILD_ID: str = _get_str_env("GUILD_ID")
TARGET_GUILD_ID: int | None = int(GUILD_ID) if GUILD_ID.isdigit() else None

# --- Display Name Styling Settings (Font, Effect, Gradient) ---
ENABLE_AUTO_STYLE: bool = _get_bool_env("ENABLE_AUTO_STYLE", True)
DEFAULT_FONT_ID: int = _get_int_env("DEFAULT_FONT_ID", 1)
DEFAULT_EFFECT_ID: int = _get_int_env("DEFAULT_EFFECT_ID", 1)
_default_colors_str = _get_str_env("DEFAULT_NAME_COLORS", "#5865F2, #EB459E, #FEE75C")
DEFAULT_HEX_COLORS: List[str] = [c.strip() for c in _default_colors_str.split(",") if c.strip()]

# --- Cloud & Web Health Check Settings ---
PORT: int = _get_int_env("PORT", 8080)
ENABLE_HEALTH_SERVER: bool = _get_bool_env("ENABLE_HEALTH_SERVER", True)

# Số lượng tác vụ AI Transcription được chạy song song tối đa (chống tràn RAM / OOM trên Cloud)
MAX_CONCURRENT_JOBS: int = _get_int_env("MAX_CONCURRENT_JOBS", 1)

# Tự động nạp trước model weights khi khởi động bot để giảm độ trễ
PRELOAD_MODEL_ON_STARTUP: bool = _get_bool_env("PRELOAD_MODEL_ON_STARTUP", True)

# Số luồng CPU sử dụng cho tính toán PyTorch khi chạy trên CPU
CPU_THREADS: int = _get_int_env("CPU_THREADS", 0)

# --- Hardware / Device Settings ---
CONFIGURED_DEVICE: str = _get_str_env("DEVICE", "auto").lower()

# --- Resource & Limit Constraints ---
MAX_FILE_SIZE_MB: int = _get_int_env("MAX_FILE_SIZE_MB", 50)
MAX_AUDIO_DURATION_SECONDS: int = _get_int_env("MAX_AUDIO_DURATION_SECONDS", 900)
DOWNLOAD_TIMEOUT_SECONDS: int = _get_int_env("DOWNLOAD_TIMEOUT_SECONDS", 180)
TRANSCRIPTION_TIMEOUT_SECONDS: int = _get_int_env("TRANSCRIPTION_TIMEOUT_SECONDS", 600)

# --- Spotify API Credentials (Tùy chọn) ---
SPOTIPY_CLIENT_ID: str = _get_str_env("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET: str = _get_str_env("SPOTIPY_CLIENT_SECRET")

# Danh sách phần mở rộng âm thanh được hỗ trợ
SUPPORTED_AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wma", ".webm", ".aiff"
}


def get_device_info() -> Tuple[str, str, bool]:
    """
    Xác định thiết bị tính toán khả dụng và trả về thông tin chi tiết.

    Returns:
        Tuple[str, str, bool]:
            - device_flag: Tham số truyền vào Transkun ('cuda' hoặc 'cpu')
            - device_display_name: Tên hiển thị thân thiện (ví dụ: 'NVIDIA GeForce RTX 3050' hoặc 'CPU Multi-threaded')
            - is_cuda: True nếu đang dùng GPU CUDA
    """
    try:
        import torch
        cuda_available = torch.cuda.is_available()
    except ImportError:
        cuda_available = False

    if CONFIGURED_DEVICE == "cuda":
        if cuda_available:
            device_name = torch.cuda.get_device_name(0)
            return "cuda", f"GPU ({device_name})", True
        else:
            logging.warning("Cấu hình yêu cầu 'cuda' nhưng không tìm thấy GPU. Tự động fallback về CPU.")
            return "cpu", "CPU (Fallback)", False

    elif CONFIGURED_DEVICE == "cpu":
        return "cpu", "CPU", False

    else:  # 'auto'
        if cuda_available:
            device_name = torch.cuda.get_device_name(0)
            return "cuda", f"GPU ({device_name})", True
        return "cpu", "CPU", False


def check_system_dependencies() -> Dict[str, bool]:
    """
    Kiểm tra các công cụ hệ thống cần thiết như FFmpeg và FFprobe.

    Returns:
        Dict[str, bool]: Trạng thái cài đặt của các công cụ.
    """
    return {
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "ffprobe": shutil.which("ffprobe") is not None,
    }
