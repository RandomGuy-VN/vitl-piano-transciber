"""
Dịch vụ tải luồng âm thanh trực tiếp từ các liên kết HTTP/HTTPS (SoundCloud, Google Drive, Hosting cá nhân)
sử dụng aiohttp và chuẩn hóa sang MP3 192kbps bằng FFmpeg.
"""

import asyncio
import logging
import os
import shutil
import subprocess
import urllib.parse
from typing import Dict, Any, Tuple
import aiohttp

from config import (
    MAX_FILE_SIZE_MB,
    DOWNLOAD_TIMEOUT_SECONDS,
)
from utils.helpers import sanitize_filename, get_audio_duration_ffprobe

logger = logging.getLogger(__name__)


class DirectDownloadService:
    """Tải và xử lý các liên kết tệp âm thanh trực tuyến bằng aiohttp."""

    @classmethod
    async def download(cls, url: str, target_dir: str) -> Tuple[str, Dict[str, Any]]:
        """
        Tải luồng âm thanh nhị phân bất đồng bộ từ URL và lưu vào target_dir.

        Args:
            url (str): Đường dẫn tải tệp âm thanh trực tiếp.
            target_dir (str): Thư mục lưu tệp tạm.

        Returns:
            Tuple[str, Dict[str, Any]]: (Đường dẫn tệp âm thanh, Dict metadata)
        """
        logger.info("Đang bắt đầu tải luồng âm thanh trực tiếp: %s", url)

        # Lấy tên file gốc từ URL
        parsed_url = urllib.parse.urlparse(url)
        raw_filename = os.path.basename(parsed_url.path) or "direct_audio.mp3"
        safe_name = sanitize_filename(os.path.splitext(raw_filename)[0])
        ext = os.path.splitext(raw_filename)[1].lower() or ".mp3"

        download_path = os.path.join(target_dir, f"raw_{safe_name}{ext}")
        final_mp3_path = os.path.join(target_dir, f"{safe_name}.mp3")

        max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        downloaded_bytes = 0

        timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT_SECONDS)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise ValueError(f"Máy chủ lưu trữ tệp trả về mã lỗi HTTP {response.status}.")

                    content_length = response.headers.get("Content-Length")
                    if content_length and int(content_length) > max_bytes:
                        raise ValueError(
                            f"Kích thước tệp âm thanh ({int(content_length) / (1024*1024):.1f} MB) vượt quá giới hạn ({MAX_FILE_SIZE_MB} MB)."
                        )

                    with open(download_path, "wb") as file:
                        async for chunk in response.content.iter_chunked(64 * 1024):
                            downloaded_bytes += len(chunk)
                            if downloaded_bytes > max_bytes:
                                raise ValueError(
                                    f"Tệp đang tải vượt quá giới hạn dung lượng cho phép ({MAX_FILE_SIZE_MB} MB)."
                                )
                            file.write(chunk)

            except aiohttp.ClientError as client_err:
                raise RuntimeError(f"Lỗi kết nối khi tải tệp từ liên kết: {client_err}") from client_err

        if not os.path.exists(download_path) or os.path.getsize(download_path) == 0:
            raise RuntimeError("Quá trình tải thất bại, không nhận được dữ liệu âm thanh hợp lệ.")

        # Chuẩn hóa file bằng FFmpeg nếu cần
        ffmpeg_bin = shutil.which("ffmpeg")
        if ffmpeg_bin and ext != ".mp3":
            try:
                cmd = [
                    ffmpeg_bin, "-y", "-i", download_path,
                    "-vn", "-ab", "192k", "-ar", "44100",
                    final_mp3_path
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await proc.wait()
                if os.path.exists(final_mp3_path):
                    try:
                        os.remove(download_path)
                    except Exception:
                        pass
                    output_file = final_mp3_path
                else:
                    output_file = download_path
            except Exception:
                output_file = download_path
        else:
            output_file = download_path

        duration = get_audio_duration_ffprobe(output_file)

        metadata = {
            "title": safe_name,
            "duration": duration,
            "uploader": parsed_url.netloc or "Direct Link",
            "webpage_url": url,
        }

        logger.info("Tải luồng âm thanh trực tiếp hoàn tất: %s (Kích thước: %d bytes)", output_file, downloaded_bytes)
        return output_file, metadata
