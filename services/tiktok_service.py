"""
Dịch vụ tải âm thanh từ TikTok bằng yt-dlp.
yt-dlp hỗ trợ TikTok native — không cần chiến lược client phức tạp như YouTube.
"""

import asyncio
import logging
import os
import shutil
import subprocess
from typing import Dict, Any, Tuple

import yt_dlp

from config import (
    MAX_AUDIO_DURATION_SECONDS,
    DOWNLOAD_TIMEOUT_SECONDS,
)
from utils.helpers import sanitize_filename

logger = logging.getLogger(__name__)


class TikTokService:
    """Trích xuất âm thanh từ video TikTok bằng yt-dlp."""

    @classmethod
    def _sync_download(cls, url: str, target_dir: str) -> Tuple[str, Dict[str, Any]]:
        """Tiến trình đồng bộ tải âm thanh TikTok qua yt-dlp."""
        logger.info("Đang tải TikTok qua yt-dlp: %s", url)

        opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "socket_timeout": 30,
            "retries": 3,
            "format": "bestaudio/best",
            "outtmpl": os.path.join(target_dir, "tiktok_%(id)s.%(ext)s"),
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)

        if info is None:
            raise RuntimeError("yt-dlp không trả về dữ liệu video TikTok.")

        duration = info.get("duration")
        if duration and duration > MAX_AUDIO_DURATION_SECONDS:
            max_mins = MAX_AUDIO_DURATION_SECONDS // 60
            raise ValueError(
                f"Thời lượng video ({int(duration)} giây) vượt quá giới hạn ({max_mins} phút)."
            )

        title = info.get("title") or "TikTok Audio"
        safe_title = sanitize_filename(title)

        # Xác định file đã tải
        downloaded = None
        req = info.get("requested_downloads") or []
        if req:
            downloaded = req[0].get("filepath") or req[0].get("filename")
        if not downloaded:
            vid = info.get("id", "")
            candidates = [
                os.path.join(target_dir, f) for f in os.listdir(target_dir)
                if vid and vid in f
            ]
            if candidates:
                downloaded = max(candidates, key=os.path.getmtime)
        if not downloaded or not os.path.exists(downloaded):
            raise RuntimeError("yt-dlp tải xong nhưng không tìm thấy file âm thanh trên đĩa.")

        # Chuẩn hóa sang WAV PCM 44.1kHz
        ffmpeg_bin = shutil.which("ffmpeg")
        final_wav = os.path.join(target_dir, f"{safe_title}.wav")
        output_file = downloaded
        if ffmpeg_bin and not downloaded.endswith(".wav"):
            try:
                subprocess.run(
                    [ffmpeg_bin, "-y", "-i", downloaded, "-vn",
                     "-acodec", "pcm_s16le", "-ar", "44100", final_wav],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                    timeout=120,
                )
                if os.path.exists(final_wav) and os.path.getsize(final_wav) > 0:
                    if downloaded != final_wav:
                        try:
                            os.remove(downloaded)
                        except Exception:
                            pass
                    output_file = final_wav
            except Exception as ffmpeg_err:
                logger.warning("Không thể chuẩn hóa bằng FFmpeg (%s), dùng file gốc.", ffmpeg_err)

        metadata = {
            "title": title,
            "duration": duration,
            "uploader": info.get("uploader") or "TikTok",
            "thumbnail": info.get("thumbnail"),
            "webpage_url": info.get("webpage_url") or url,
        }

        logger.info("Tải thành công từ TikTok: %s (File: %s)", title, output_file)
        return output_file, metadata

    @classmethod
    async def download(cls, url: str, target_dir: str) -> Tuple[str, Dict[str, Any]]:
        """Tải âm thanh bất đồng bộ từ liên kết TikTok."""
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(cls._sync_download, url, target_dir),
                timeout=DOWNLOAD_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Quá thời gian tải âm thanh từ TikTok ({DOWNLOAD_TIMEOUT_SECONDS}s). Vui lòng thử lại sau."
            )
