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

# --- Discord Bot Settings ---
DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "").strip()
GUILD_ID: str = os.getenv("GUILD_ID", "").strip()
TARGET_GUILD_ID: int | None = int(GUILD_ID) if GUILD_ID.isdigit() else None

# --- Display Name Styling Settings (Font, Effect, Gradient) ---
ENABLE_AUTO_STYLE: bool = os.getenv("ENABLE_AUTO_STYLE", "true").lower() in ("true", "1", "yes")
DEFAULT_FONT_ID: int = int(os.getenv("DEFAULT_FONT_ID", "1"))
DEFAULT_EFFECT_ID: int = int(os.getenv("DEFAULT_EFFECT_ID", "1"))
_default_colors_str = os.getenv("DEFAULT_NAME_COLORS", "#5865F2, #EB459E, #FEE75C").strip()
DEFAULT_HEX_COLORS: List[str] = [c.strip() for c in _default_colors_str.split(",") if c.strip()]

# --- Cloud & Web Health Check Settings ---
# Cổng chạy Web Server báo trạng thái cho Cloud PaaS (Railway, Render, Fly.io, Koyeb, K8s)
PORT: int = int(os.getenv("PORT", "8080"))
ENABLE_HEALTH_SERVER: bool = os.getenv("ENABLE_HEALTH_SERVER", "true").lower() in ("true", "1", "yes")

# Số lượng tác vụ AI Transcription được chạy song song tối đa (để chống tràn RAM / OOM trên Cloud)
MAX_CONCURRENT_JOBS: int = int(os.getenv("MAX_CONCURRENT_JOBS", "1"))

# Tự động tải trước (preload) model weights khi khởi động bot để giảm độ trễ cho người dùng đầu tiên
PRELOAD_MODEL_ON_STARTUP: bool = os.getenv("PRELOAD_MODEL_ON_STARTUP", "true").lower() in ("true", "1", "yes")

# Số luồng CPU sử dụng cho tính toán PyTorch khi chạy trên CPU
CPU_THREADS: int = int(os.getenv("CPU_THREADS", "0"))  # 0: để PyTorch tự động chọn theo số vCPU

# --- Hardware / Device Settings ---
# Cấu hình thiết bị xử lý: 'auto', 'cuda', hoặc 'cpu'
CONFIGURED_DEVICE: str = os.getenv("DEVICE", "auto").strip().lower()

# --- Resource & Limit Constraints ---
# Giới hạn kích thước file upload (MB)
MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))

# Giới hạn thời lượng tối đa cho file âm thanh (giây) - Mặc định 15 phút (900 giây)
MAX_AUDIO_DURATION_SECONDS: int = int(os.getenv("MAX_AUDIO_DURATION_SECONDS", "900"))

# Thời gian timeout cho quá trình tải nhạc (giây)
DOWNLOAD_TIMEOUT_SECONDS: int = int(os.getenv("DOWNLOAD_TIMEOUT_SECONDS", "180"))

# Thời gian timeout cho quá trình AI transcription (giây)
TRANSCRIPTION_TIMEOUT_SECONDS: int = int(os.getenv("TRANSCRIPTION_TIMEOUT_SECONDS", "600"))

# --- Spotify API Credentials (Tùy chọn) ---
SPOTIPY_CLIENT_ID: str = os.getenv("SPOTIPY_CLIENT_ID", "").strip()
SPOTIPY_CLIENT_SECRET: str = os.getenv("SPOTIPY_CLIENT_SECRET", "").strip()

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
