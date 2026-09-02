"""
Dịch vụ điều phối tải và chuẩn bị file âm thanh đầu vào từ mọi nguồn (Discord Attachment hoặc URL).
Sử dụng pytubefix cho YouTube, SpotifyService (oEmbed + pytubefix search) cho Spotify và DirectDownloadService cho Direct Audio links.
Hoàn toàn độc lập, không phụ thuộc vào yt-dlp hay spotdl.
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional
import discord

from config import (
    MAX_FILE_SIZE_MB,
    MAX_AUDIO_DURATION_SECONDS,
    SUPPORTED_AUDIO_EXTENSIONS,
)
from services.youtube_service import YouTubeService
from services.spotify_service import SpotifyService
from services.direct_download_service import DirectDownloadService
from utils.helpers import (
    is_spotify_url,
    is_youtube_url,
    is_valid_url,
    detect_source_name,
    get_audio_duration_ffprobe,
    sanitize_filename,
)

logger = logging.getLogger(__name__)


@dataclass
class AudioSourceInfo:
    """Thông tin chi tiết về file âm thanh đã được chuẩn bị sẵn sàng cho AI transcription."""
    file_path: str
    title: str
    duration_sec: Optional[float]
    source_type: str
    source_label: str
    uploader: Optional[str] = None
    original_url: Optional[str] = None


class AudioFetcher:
    """Điều phối và tải file âm thanh từ Attachment hoặc URL."""

    @classmethod
    async def fetch_attachment(
        cls,
        attachment: discord.Attachment,
        target_dir: str
    ) -> AudioSourceInfo:
        """
        Xử lý và tải tệp âm thanh đính kèm trực tiếp từ tin nhắn Discord.

        Args:
            attachment (discord.Attachment): Đối tượng tệp đính kèm của Discord.
            target_dir (str): Thư mục lưu trữ tạm.

        Returns:
            AudioSourceInfo: Đối tượng chứa thông tin tệp âm thanh đã tải.
        """
        logger.info("Đang xử lý tệp đính kèm: %s (Kích thước: %d bytes)", attachment.filename, attachment.size)

        # 1. Kiểm tra kích thước tệp
        max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        if attachment.size > max_bytes:
            raise ValueError(
                f"Kích thước tệp đính kèm ({attachment.size / (1024*1024):.1f} MB) vượt quá giới hạn cho phép ({MAX_FILE_SIZE_MB} MB)."
            )

        # 2. Kiểm tra phần mở rộng định dạng file
        ext = os.path.splitext(attachment.filename)[1].lower()
        if ext not in SUPPORTED_AUDIO_EXTENSIONS:
            supported_str = ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
            raise ValueError(
                f"Định dạng tệp `{ext}` không được hỗ trợ.\nCác định dạng cho phép: `{supported_str}`"
            )

        # 3. Lưu file vào thư mục tạm
        safe_name = sanitize_filename(os.path.splitext(attachment.filename)[0])
        saved_file_path = os.path.join(target_dir, f"{safe_name}{ext}")
        await attachment.save(saved_file_path)

        # 4. Đo thời lượng file âm thanh
        duration = get_audio_duration_ffprobe(saved_file_path)
        if duration and duration > MAX_AUDIO_DURATION_SECONDS:
            max_mins = MAX_AUDIO_DURATION_SECONDS // 60
            raise ValueError(
                f"Thời lượng tệp âm thanh ({int(duration)} giây) vượt quá giới hạn ({max_mins} phút)."
            )

        return AudioSourceInfo(
            file_path=saved_file_path,
            title=attachment.filename,
            duration_sec=duration,
            source_type="Tệp tải lên",
            source_label=attachment.filename,
            uploader="Discord User"
        )

    @classmethod
    async def fetch_url(cls, url: str, target_dir: str) -> AudioSourceInfo:
        """
        Xử lý và tải âm thanh từ URL trực tuyến (Spotify, YouTube, SoundCloud, v.v.).

        Args:
            url (str): Đường dẫn URL.
            target_dir (str): Thư mục lưu trữ tạm.

        Returns:
            AudioSourceInfo: Đối tượng chứa thông tin tệp âm thanh đã tải.
        """
        cleaned_url = url.strip()
        if not is_valid_url(cleaned_url):
            raise ValueError("Đường dẫn (URL) không hợp lệ. Vui lòng cung cấp link bắt đầu bằng `http://` hoặc `https://`.")

        source_type = detect_source_name(cleaned_url)

        if is_spotify_url(cleaned_url):
            file_path, meta = await SpotifyService.download(cleaned_url, target_dir)
        elif is_youtube_url(cleaned_url):
            file_path, meta = await YouTubeService.download(cleaned_url, target_dir)
        else:
            file_path, meta = await DirectDownloadService.download(cleaned_url, target_dir)

        # Cập nhật thời lượng nếu chưa có trong metadata
        duration = meta.get("duration")
        if duration is None:
            duration = get_audio_duration_ffprobe(file_path)

        return AudioSourceInfo(
            file_path=file_path,
            title=meta.get("title", "Unknown Audio"),
            duration_sec=duration,
            source_type=source_type,
            source_label=cleaned_url,
            uploader=meta.get("uploader"),
            original_url=cleaned_url
        )
