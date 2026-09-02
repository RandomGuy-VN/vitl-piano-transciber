"""
Dịch vụ tải và trích xuất âm thanh từ YouTube, SoundCloud và các nguồn trực tiếp bằng yt-dlp.
"""

import asyncio
import os
import glob
import logging
from typing import Dict, Any, Tuple, Optional
import yt_dlp

from config import (
    MAX_AUDIO_DURATION_SECONDS,
    MAX_FILE_SIZE_MB,
    DOWNLOAD_TIMEOUT_SECONDS,
)
from utils.helpers import sanitize_filename

logger = logging.getLogger(__name__)


class YtDlpService:
    """Xử lý tải âm thanh từ các nền tảng hỗ trợ qua yt-dlp với chuẩn MP3 192kbps."""

    @staticmethod
    def _get_ydl_options(output_template: str) -> Dict[str, Any]:
        """Tạo cấu hình tối ưu cho yt-dlp."""
        return {
            "format": "bestaudio/best",
            "outtmpl": output_template,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": False,
            "nocheckcertificate": True,
            "max_filesize": MAX_FILE_SIZE_MB * 1024 * 1024,
            # Giới hạn tìm kiếm và trích xuất thông tin nhanh
            "extract_flat": False,
        }

    @classmethod
    def _sync_download(cls, url: str, target_dir: str) -> Tuple[str, Dict[str, Any]]:
        """
        Tiến trình đồng bộ tải và chuyển đổi âm thanh bằng yt-dlp.
        Được gọi bên trong asyncio.to_thread để tránh nghẽn luồng chính.
        """
        output_template = os.path.join(target_dir, "%(id)s_%(title).60s.%(ext)s")
        ydl_opts = cls._get_ydl_options(output_template)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 1. Trích xuất thông tin trước
            logger.info("Đang trích xuất siêu dữ liệu từ URL: %s", url)
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as exc:
                err_msg = str(exc)
                if "is not a valid URL" in err_msg or "Unsupported URL" in err_msg:
                    raise ValueError(f"Đường dẫn không hợp lệ hoặc không được hỗ trợ bởi yt-dlp: {url}") from exc
                if "Private video" in err_msg or "Sign in to confirm your age" in err_msg:
                    raise ValueError("Video ở chế độ riêng tư hoặc yêu cầu xác minh độ tuổi.") from exc
                raise RuntimeError(f"Lỗi khi trích xuất thông tin: {err_msg}") from exc

            if not info:
                raise RuntimeError("Không lấy được dữ liệu âm thanh từ URL đã cung cấp.")

            # Kiểm tra nếu là danh sách phát (playlist)
            if "entries" in info and info["entries"]:
                info = info["entries"][0]

            # Kiểm tra nếu là livestream
            if info.get("is_live"):
                raise ValueError("Không hỗ trợ xử lý luồng phát trực tiếp (livestream).")

            # Kiểm tra thời lượng
            duration = info.get("duration")
            if duration and duration > MAX_AUDIO_DURATION_SECONDS:
                max_mins = MAX_AUDIO_DURATION_SECONDS // 60
                raise ValueError(
                    f"Thời lượng tác phẩm ({int(duration)} giây) vượt quá giới hạn cho phép ({max_mins} phút)."
                )

            # 2. Thực hiện tải xuống và chuyển đổi sang MP3
            logger.info("Đang tải file âm thanh: %s", info.get("title", "Unknown"))
            ydl.download([url])

            # 3. Tìm file mp3 kết quả trong target_dir
            mp3_files = glob.glob(os.path.join(target_dir, "*.mp3"))
            if not mp3_files:
                # Tìm bất kỳ file âm thanh nào khác nếu ffmpeg không tạo mp3
                all_files = [
                    os.path.join(target_dir, f)
                    for f in os.listdir(target_dir)
                    if os.path.isfile(os.path.join(target_dir, f))
                ]
                if not all_files:
                    raise FileNotFoundError("Quá trình tải hoàn tất nhưng không tìm thấy file âm thanh đầu ra.")
                downloaded_file = all_files[0]
            else:
                downloaded_file = mp3_files[0]

            metadata = {
                "title": info.get("title") or "Unknown Track",
                "duration": duration,
                "uploader": info.get("uploader") or info.get("channel") or "Unknown Artist",
                "thumbnail": info.get("thumbnail"),
                "webpage_url": info.get("webpage_url") or url,
            }

            return downloaded_file, metadata

    @classmethod
    async def download(cls, url: str, target_dir: str) -> Tuple[str, Dict[str, Any]]:
        """
        Tải âm thanh bất đồng bộ từ URL bằng yt-dlp.

        Args:
            url (str): Đường dẫn cần tải.
            target_dir (str): Thư mục lưu trữ tạm thời.

        Returns:
            Tuple[str, Dict[str, Any]]: (Đường dẫn file âm thanh, Dictionary metadata)
        """
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(cls._sync_download, url, target_dir),
                timeout=DOWNLOAD_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Quá thời gian tải âm thanh ({DOWNLOAD_TIMEOUT_SECONDS}s). Vui lòng thử lại sau hoặc chọn nguồn khác."
            )
