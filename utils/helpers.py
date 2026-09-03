"""
Các hàm tiện ích hỗ trợ xử lý chuỗi, định dạng dung lượng, thời lượng, kiểm tra URL và trích xuất siêu dữ liệu tệp tin.
"""

import os
import re
import shutil
import subprocess
import urllib.parse
from typing import Optional


def format_bytes(size_bytes: int) -> str:
    """
    Định dạng số byte sang đơn vị đọc được (B, KB, MB, GB).

    Args:
        size_bytes (int): Kích thước tính bằng byte.

    Returns:
        str: Chuỗi dung lượng định dạng (ví dụ: '2.45 MB', '54.2 KB').
    """
    if size_bytes < 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    return f"{size:.2f} {units[unit_index]}"


def format_duration(seconds: Optional[float | int]) -> str:
    """
    Định dạng số giây thành chuỗi thời lượng dạng MM:SS hoặc HH:MM:SS.

    Args:
        seconds (Optional[float | int]): Thời gian tính bằng giây.

    Returns:
        str: Thời gian hiển thị (ví dụ: '03:45' hoặc '01:12:30').
    """
    if seconds is None or seconds < 0:
        return "Không rõ"

    total_seconds = int(round(seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_elapsed_time(seconds: float) -> str:
    """
    Định dạng thời gian thực thi (giây) thành chuỗi trực quan.

    Args:
        seconds (float): Số giây thực thi.

    Returns:
        str: Chuỗi hiển thị (ví dụ: '8.4s' hoặc '1m 24.3s').
    """
    if seconds < 0:
        return "0.0s"
    if seconds < 60:
        return f"{seconds:.1f}s"
    mins = int(seconds // 60)
    rem_secs = seconds % 60
    return f"{mins}m {rem_secs:.1f}s"


def sanitize_filename(name: str, max_length: int = 80) -> str:
    """
    Làm sạch chuỗi để dùng làm tên tệp tin an toàn trên hệ điều hành.

    Args:
        name (str): Tên file thô.
        max_length (int): Độ dài tối đa của tên file.

    Returns:
        str: Tên file đã được làm sạch và chuẩn hóa.
    """
    # Loại bỏ các ký tự đặc biệt nguy hiểm hoặc không hợp lệ
    clean_name = re.sub(r'[\\/*?:"<>|]', "", name)
    clean_name = re.sub(r"\s+", " ", clean_name).strip()
    if not clean_name:
        clean_name = "transcription"
    # Giới hạn độ dài để không bị tràn tên file
    return clean_name[:max_length]


def is_spotify_url(url: str) -> bool:
    """
    Kiểm tra xem một URL có phải từ Spotify hay không.

    Args:
        url (str): Chuỗi URL cần kiểm tra.

    Returns:
        bool: True nếu là link Spotify, ngược lại False.
    """
    if not url:
        return False
    parsed = urllib.parse.urlparse(url.strip())
    domain = parsed.netloc.lower()
    return any(d in domain for d in ["spotify.com", "spotify.link", "spoti.fi"])


def is_youtube_url(url: str) -> bool:
    """
    Kiểm tra xem một URL có phải từ YouTube hay không.

    Args:
        url (str): Chuỗi URL cần kiểm tra.

    Returns:
        bool: True nếu là link YouTube, ngược lại False.
    """
    if not url:
        return False
    parsed = urllib.parse.urlparse(url.strip())
    domain = parsed.netloc.lower()
    return any(d in domain for d in ["youtube.com", "youtu.be", "music.youtube.com"])


def is_soundcloud_url(url: str) -> bool:
    """
    Kiểm tra xem một URL có phải từ SoundCloud hay không.

    Args:
        url (str): Chuỗi URL cần kiểm tra.

    Returns:
        bool: True nếu là link SoundCloud, ngược lại False.
    """
    if not url:
        return False
    parsed = urllib.parse.urlparse(url.strip())
    domain = parsed.netloc.lower()
    return any(d in domain for d in ["soundcloud.com", "on.soundcloud.com"])


def is_valid_url(url: str) -> bool:
    """
    Kiểm tra xem chuỗi có phải là một URL HTTP/HTTPS hợp lệ hay không.

    Args:
        url (str): Chuỗi cần kiểm tra.

    Returns:
        bool: True nếu là URL hợp lệ.
    """
    if not url:
        return False
    try:
        result = urllib.parse.urlparse(url.strip())
        return result.scheme in ("http", "https") and bool(result.netloc)
    except Exception:
        return False


def detect_source_name(url: str) -> str:
    """
    Xác định tên dịch vụ hoặc nguồn phát từ URL đầu vào.

    Args:
        url (str): Đường dẫn URL.

    Returns:
        str: Tên dịch vụ hiển thị (YouTube, Spotify, SoundCloud, v.v.).
    """
    if not url:
        return "Tệp tải lên"
    domain = urllib.parse.urlparse(url.strip()).netloc.lower()
    if "youtube.com" in domain or "youtu.be" in domain:
        return "YouTube"
    if "spotify.com" in domain or "spotify.link" in domain or "spoti.fi" in domain:
        return "Spotify"
    if "soundcloud.com" in domain:
        return "SoundCloud"
    if "bilibili.com" in domain or "b23.tv" in domain:
        return "Bilibili"
    if "tiktok.com" in domain:
        return "TikTok"
    if "facebook.com" in domain or "fb.watch" in domain:
        return "Facebook"
    if "drive.google.com" in domain:
        return "Google Drive"
    return "Đường dẫn trực tiếp"


def get_audio_duration_ffprobe(file_path: str) -> Optional[float]:
    """
    Sử dụng công cụ ffprobe để đọc chính xác thời lượng của file âm thanh cục bộ.

    Args:
        file_path (str): Đường dẫn tuyệt đối tới file âm thanh.

    Returns:
        Optional[float]: Thời lượng file tính theo giây hoặc None nếu không đọc được.
    """
    ffprobe_bin = shutil.which("ffprobe")
    if not ffprobe_bin or not os.path.exists(file_path):
        return None

    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            check=True
        )
        duration_str = result.stdout.strip()
        if duration_str:
            return float(duration_str)
    except Exception:
        return None
    return None
