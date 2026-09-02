"""
Dịch vụ tải âm thanh từ YouTube sử dụng thư viện pytubefix (thay thế cho yt-dlp).
Tối ưu hóa tránh IP Ban từ YouTube trên môi trường Cloud / GitHub Actions.
"""

import asyncio
import logging
import os
import shutil
import subprocess
from typing import Dict, Any, Tuple, Optional
from pytubefix import YouTube
from pytubefix.exceptions import (
    VideoUnavailable,
    AgeRestrictedError,
    LiveStreamError,
    RegexMatchError,
)

from config import (
    MAX_AUDIO_DURATION_SECONDS,
    DOWNLOAD_TIMEOUT_SECONDS,
)
from utils.helpers import sanitize_filename

logger = logging.getLogger(__name__)


class YouTubeService:
    """Xử lý trích xuất âm thanh từ YouTube bằng pytubefix."""

    @classmethod
    def _sync_download(cls, url: str, target_dir: str) -> Tuple[str, Dict[str, Any]]:
        """
        Tiến trình đồng bộ tải và chuyển đổi âm thanh từ YouTube.
        Chạy trong asyncio.to_thread để không làm nghẽn Event Loop.
        """
        logger.info("Đang khởi tạo kết nối tải YouTube qua pytubefix: %s", url)

        try:
            # Khởi tạo đối tượng YouTube với client WEB (hoặc fallback clients)
            yt = YouTube(url, client='WEB')
        except RegexMatchError as reg_err:
            raise ValueError(f"Đường dẫn YouTube không đúng định dạng: {url}") from reg_err
        except Exception as init_err:
            raise RuntimeError(f"Không thể kết nối đến video YouTube: {init_err}") from init_err

        # 1. Kiểm tra tính khả dụng của video
        try:
            yt.check_availability()
        except LiveStreamError:
            raise ValueError("Không hỗ trợ xử lý luồng phát trực tiếp (Live Stream).")
        except AgeRestrictedError:
            # Thử lại với client Android/TV nếu bị giới hạn độ tuổi
            try:
                yt = YouTube(url, client='ANDROID')
            except Exception:
                raise ValueError("Video này bị giới hạn độ tuổi và yêu cầu đăng nhập.")
        except VideoUnavailable:
            raise ValueError("Video YouTube này không khả dụng hoặc đã bị xóa / chuyển sang chế độ riêng tư.")
        except Exception as avail_err:
            logger.warning("Cảnh báo kiểm tra tính khả dụng: %s", avail_err)

        # 2. Kiểm tra thời lượng bài hát
        duration = yt.length
        if duration and duration > MAX_AUDIO_DURATION_SECONDS:
            max_mins = MAX_AUDIO_DURATION_SECONDS // 60
            raise ValueError(
                f"Thời lượng tác phẩm ({int(duration)} giây) vượt quá giới hạn cho phép ({max_mins} phút)."
            )

        # 3. Lấy luồng âm thanh tốt nhất
        audio_stream = yt.streams.get_audio_only()
        if not audio_stream:
            raise RuntimeError("Không tìm thấy luồng âm thanh (audio stream) khả dụng cho video này.")

        title = yt.title or "YouTube Audio"
        safe_title = sanitize_filename(title)
        temp_download_name = f"yt_{safe_title}.m4a"
        final_mp3_path = os.path.join(target_dir, f"{safe_title}.mp3")

        logger.info("Đang tải luồng âm thanh: %s (Kích thước: %s bytes)", title, audio_stream.filesize)

        # Tải tệp âm thanh gốc về thư mục tạm
        downloaded_raw_path = audio_stream.download(
            output_path=target_dir,
            filename=temp_download_name
        )

        # 4. Chuẩn hóa sang file MP3 192kbps bằng FFmpeg
        ffmpeg_bin = shutil.which("ffmpeg")
        if ffmpeg_bin and os.path.exists(downloaded_raw_path):
            try:
                cmd = [
                    ffmpeg_bin,
                    "-y",
                    "-i", downloaded_raw_path,
                    "-vn",
                    "-ab", "192k",
                    "-ar", "44100",
                    final_mp3_path
                ]
                subprocess.run(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                    timeout=60
                )
                # Xóa tệp thô trung gian
                if os.path.exists(downloaded_raw_path) and downloaded_raw_path != final_mp3_path:
                    try:
                        os.remove(downloaded_raw_path)
                    except Exception:
                        pass
                output_file = final_mp3_path
            except Exception as ffmpeg_err:
                logger.warning("Không thể chuyển đổi bằng FFmpeg (%s), sử dụng tệp thô tải về.", ffmpeg_err)
                output_file = downloaded_raw_path
        else:
            output_file = downloaded_raw_path

        metadata = {
            "title": title,
            "duration": duration,
            "uploader": yt.author or "YouTube",
            "thumbnail": yt.thumbnail_url,
            "webpage_url": url,
        }

        logger.info("Tải thành công từ YouTube qua pytubefix: %s (File: %s)", title, output_file)
        return output_file, metadata

    @classmethod
    async def download(cls, url: str, target_dir: str) -> Tuple[str, Dict[str, Any]]:
        """
        Tải âm thanh bất đồng bộ từ liên kết YouTube bằng pytubefix.

        Args:
            url (str): Đường dẫn video YouTube.
            target_dir (str): Thư mục lưu file tạm.

        Returns:
            Tuple[str, Dict[str, Any]]: (Đường dẫn file âm thanh, Dict metadata)
        """
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(cls._sync_download, url, target_dir),
                timeout=DOWNLOAD_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Quá thời gian tải âm thanh từ YouTube ({DOWNLOAD_TIMEOUT_SECONDS}s). Vui lòng thử lại sau."
            )
