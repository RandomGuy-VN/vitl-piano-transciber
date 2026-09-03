"""
Dịch vụ tải âm thanh từ SoundCloud sử dụng thư viện scdl.
Hỗ trợ tải trực tiếp các track từ soundcloud.com và on.soundcloud.com với chất lượng cao.
"""

import asyncio
import glob
import logging
import os
import re
import sys
from typing import Dict, Any, Tuple, Optional

from config import (
    MAX_AUDIO_DURATION_SECONDS,
    DOWNLOAD_TIMEOUT_SECONDS,
    SUPPORTED_AUDIO_EXTENSIONS,
)
from utils.helpers import (
    sanitize_filename,
    get_audio_duration_ffprobe,
    is_soundcloud_url,
)

logger = logging.getLogger(__name__)


class SoundCloudService:
    """Xử lý tải bài hát từ SoundCloud bằng công cụ scdl."""

    @classmethod
    async def download(cls, url: str, target_dir: str) -> Tuple[str, Dict[str, Any]]:
        """
        Tải bài hát bất đồng bộ từ liên kết SoundCloud bằng scdl.

        Args:
            url (str): Đường dẫn track SoundCloud.
            target_dir (str): Thư mục lưu file tạm.

        Returns:
            Tuple[str, Dict[str, Any]]: (Đường dẫn file âm thanh, Dict metadata)
        """
        cleaned_url = url.strip()
        if not is_soundcloud_url(cleaned_url):
            raise ValueError(f"Đường dẫn không phải là liên kết SoundCloud hợp lệ: {url}")

        logger.info("Bắt đầu tải nhạc SoundCloud qua scdl: %s", cleaned_url)

        # Lệnh gọi scdl thông qua entrypoint Python chuẩn hóa
        cmd = [
            sys.executable,
            "-c",
            "import sys; from scdl.scdl import _main; sys.exit(_main())",
            "-l",
            cleaned_url,
            "--path",
            target_dir,
            "--onlymp3",
            "--overwrite",
            "--hide-progress",
            "--no-playlist",
        ]

        try:
            # Chạy scdl dưới dạng asyncio subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=DOWNLOAD_TIMEOUT_SECONDS,
            )

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            if process.returncode != 0:
                err_snippet = (stderr_str or stdout_str).strip()
                logger.error("scdl trả về mã lỗi %d: %s", process.returncode, err_snippet)
                raise RuntimeError(
                    f"scdl không thể tải bài hát từ SoundCloud: {err_snippet[-300:] if err_snippet else 'Lỗi không xác định'}"
                )

        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Quá thời gian tải âm thanh từ SoundCloud ({DOWNLOAD_TIMEOUT_SECONDS}s). Vui lòng thử lại sau."
            )

        # Quét thư mục target_dir để tìm file âm thanh được tải về
        found_audio_files = []
        for file_name in os.listdir(target_dir):
            file_path = os.path.join(target_dir, file_name)
            if not os.path.isfile(file_path):
                continue
            ext = os.path.splitext(file_name)[1].lower()
            if ext in SUPPORTED_AUDIO_EXTENSIONS:
                found_audio_files.append(file_path)

        if not found_audio_files:
            logger.error("scdl hoàn thành nhưng không tìm thấy file âm thanh trong %s", target_dir)
            raise FileNotFoundError("Không tìm thấy tệp âm thanh nào được tải về từ SoundCloud.")

        # Lấy file âm thanh mới nhất hoặc lớn nhất
        chosen_audio_file = max(found_audio_files, key=os.path.getsize)

        # Lấy tên file gốc và làm sạch để làm tiêu đề
        raw_name = os.path.splitext(os.path.basename(chosen_audio_file))[0]
        # scdl thường lưu dạng "[id] Artist - Title" -> trích xuất phần Artist - Title
        clean_title = re.sub(r"^\[\d+\]\s*", "", raw_name).strip()
        if not clean_title:
            clean_title = sanitize_filename(raw_name)

        # Đo thời lượng âm thanh bằng ffprobe
        duration = get_audio_duration_ffprobe(chosen_audio_file)
        if duration and duration > MAX_AUDIO_DURATION_SECONDS:
            max_mins = MAX_AUDIO_DURATION_SECONDS // 60
            raise ValueError(
                f"Thời lượng bài hát ({int(duration)} giây) vượt quá giới hạn cho phép ({max_mins} phút)."
            )

        # Trích xuất artist nếu có định dạng "Artist - Title"
        uploader = "SoundCloud Artist"
        if " - " in clean_title:
            parts = clean_title.split(" - ", 1)
            uploader = parts[0].strip()

        metadata = {
            "title": clean_title,
            "duration": duration,
            "uploader": uploader,
            "original_url": cleaned_url,
            "source_type": "SoundCloud",
        }

        logger.info(
            "Tải thành công từ SoundCloud qua scdl: %s (Thời lượng: %ss, File: %s)",
            clean_title,
            duration,
            chosen_audio_file,
        )
        return chosen_audio_file, metadata
