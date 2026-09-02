"""
Dịch vụ tải nhạc từ Spotify sử dụng spotdl kết hợp subprocess bất đồng bộ.
"""

import asyncio
import glob
import logging
import os
import sys
from typing import Dict, Any, Tuple, Optional

from config import (
    DOWNLOAD_TIMEOUT_SECONDS,
    SPOTIPY_CLIENT_ID,
    SPOTIPY_CLIENT_SECRET,
)
from utils.helpers import get_audio_duration_ffprobe

logger = logging.getLogger(__name__)


class SpotDlService:
    """Xử lý tải âm thanh từ các liên kết Spotify qua spotdl CLI/module."""

    @classmethod
    async def download(cls, url: str, target_dir: str) -> Tuple[str, Dict[str, Any]]:
        """
        Tải bài hát từ liên kết Spotify về thư mục tạm dưới định dạng MP3.

        Args:
            url (str): Liên kết Spotify (Track, Album, Playlist).
            target_dir (str): Thư mục lưu trữ tạm thời.

        Returns:
            Tuple[str, Dict[str, Any]]: (Đường dẫn file MP3, Dict metadata)
        """
        logger.info("Bắt đầu xử lý tải nhạc Spotify qua spotdl: %s", url)

        # Chuẩn bị biến môi trường (truyền Spotify Client credentials nếu có)
        env = os.environ.copy()
        if SPOTIPY_CLIENT_ID:
            env["SPOTIPY_CLIENT_ID"] = SPOTIPY_CLIENT_ID
        if SPOTIPY_CLIENT_SECRET:
            env["SPOTIPY_CLIENT_SECRET"] = SPOTIPY_CLIENT_SECRET

        output_template = os.path.join(target_dir, "{artist} - {title}.{output-ext}")

        # Lệnh chạy spotdl dạng subprocess non-blocking
        cmd = [
            sys.executable,
            "-m",
            "spotdl",
            "download",
            url,
            "--output",
            output_template,
            "--format",
            "mp3",
        ]

        logger.debug("Thực thi lệnh spotdl: %s", " ".join(cmd))

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=target_dir
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=DOWNLOAD_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError:
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass
                raise TimeoutError(
                    f"Quá thời gian tải nhạc từ Spotify ({DOWNLOAD_TIMEOUT_SECONDS}s). Vui lòng thử lại."
                )

            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")

            if process.returncode != 0:
                logger.error("spotdl thất bại (code %d): %s\n%s", process.returncode, stdout_text, stderr_text)
                combined_err = f"{stderr_text}\n{stdout_text}".strip()
                if "No results found" in combined_err or "Song not found" in combined_err:
                    raise ValueError(f"Không tìm thấy bài hát tương ứng trên Spotify cho liên kết: {url}")
                if "spotdl: error" in combined_err or "ModuleNotFoundError" in combined_err:
                    raise RuntimeError("Công cụ spotdl chưa được cài đặt hoặc gặp lỗi cấu hình môi trường.")
                raise RuntimeError(f"Lỗi khi tải từ Spotify: {combined_err[:300]}")

            # Tìm file mp3 đã tải về trong target_dir
            mp3_files = glob.glob(os.path.join(target_dir, "*.mp3"))
            if not mp3_files:
                # Tìm tất cả file trong target_dir
                all_files = [
                    os.path.join(target_dir, f)
                    for f in os.listdir(target_dir)
                    if os.path.isfile(os.path.join(target_dir, f)) and not f.endswith(".spotdl-cache")
                ]
                if not all_files:
                    raise FileNotFoundError("Không tìm thấy file nhạc sau khi spotdl hoàn tất tải về.")
                downloaded_file = all_files[0]
            else:
                downloaded_file = mp3_files[0]

            # Lấy tên bài hát từ tên file
            base_name = os.path.splitext(os.path.basename(downloaded_file))[0]
            duration = get_audio_duration_ffprobe(downloaded_file)

            metadata = {
                "title": base_name,
                "duration": duration,
                "uploader": "Spotify",
                "webpage_url": url,
            }

            logger.info("Tải thành công từ Spotify: %s (Duration: %s)", downloaded_file, duration)
            return downloaded_file, metadata

        except Exception as exc:
            if not isinstance(exc, (ValueError, TimeoutError, RuntimeError, FileNotFoundError)):
                logger.exception("Lỗi không mong muốn trong SpotDlService: %s", exc)
            raise
