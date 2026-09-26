"""
Dịch vụ tải âm thanh từ YouTube bằng yt-dlp (phiên bản đã xác minh hoạt động
từ IP datacenter với cookies + PO Token + EJS solver).

Chiến lược client thử lần lượt: android -> android_vr -> web(+cookies) ->
tv -> tv_simply -> default. Bot-check của YouTube "flaky" nên đa chiến lược
+ retry giúp tỷ lệ thành công cao.
"""

import asyncio
import logging
import os
import shutil
import subprocess
from typing import Dict, Any, Tuple, Optional, List

import yt_dlp

from config import (
    MAX_AUDIO_DURATION_SECONDS,
    DOWNLOAD_TIMEOUT_SECONDS,
)
from utils.helpers import sanitize_filename

logger = logging.getLogger(__name__)

# Các chiến lược client YouTube được thử lần lượt.
# WEB client (cookies + EJS solver + POT server) đã được xác minh hoạt động từ IP datacenter.
CLIENT_STRATEGIES: List[Optional[List[str]]] = [
    ["android"],       # 1. Android client — KHÔNG cần POT, native downloader tải full speed
    ["android_vr"],    # 2. Android VR client — dự phòng ẩn danh
    ["web"],           # 3. Web client + cookies + PO Token + EJS (cần cho age-restricted)
    ["tv"],            # 4. YouTube TV client (dự phòng)
    ["tv_simply"],     # 5. TV Simply client (dự phòng)
    None,              # 6. Mặc định của yt-dlp (auto)
]

_STRATEGY_LABELS = {
    0: "ANDROID",
    1: "ANDROID_VR",
    2: "WEB",
    3: "TV",
    4: "TV_SIMPLY",
    5: "DEFAULT",
}

# Các client KHÔNG được dùng cookies (Google có thể khóa tài khoản nếu cookie
# đăng nhập bị dùng kèm client không phải web; android family vốn ẩn danh).
_NO_COOKIE_CLIENTS = {"android", "android_vr"}


def get_cookies_file() -> Optional[str]:
    """
    Tìm file cookies YouTube (định dạng Netscape) theo thứ tự ưu tiên:
    1. Biến môi trường YT_COOKIES_FILE (đường dẫn tùy chỉnh)
    2. File cookies.txt tại thư mục gốc dự án
    Returns đường dẫn nếu tồn tại, ngược lại None.
    """
    env_path = os.getenv("YT_COOKIES_FILE", "").strip()
    if env_path and os.path.isfile(env_path):
        return env_path
    project_cookies = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cookies.txt"
    )
    if os.path.isfile(project_cookies):
        return project_cookies
    return None


def _backup_cookies() -> None:
    """
    Backup file cookies sau mỗi lần tải thành công.

    YouTube xoay (rotate) các cookie phiên (1PSIDTS/3PSIDTS) liên tục; yt-dlp
    ghi ngược giá trị mới vào cookiefile sau khi dùng. Nếu cookiefile bị mất/
    ghi đè, có thể khôi phục từ bản .auto-bak gần nhất.
    """
    try:
        cookies_path = get_cookies_file()
        if cookies_path and os.path.isfile(cookies_path):
            backup_path = cookies_path + ".auto-bak"
            shutil.copy2(cookies_path, backup_path)
    except OSError as e:
        logger.warning("Không backup được cookies: %s", e)


def _friendly_yt_error(err_msg: str, url: str) -> str:
    """Chuyển lỗi thô của yt-dlp thành thông điệp thân thiện tiếng Việt."""
    low = err_msg.lower()
    if "sign in to confirm" in low and ("bot" in low or "not a bot" in low):
        return (
            "YouTube đang chặn truy cập từ máy chủ (bot-check). "
            "Vui lòng thử lại sau ít phút hoặc dùng file âm thanh tải lên trực tiếp."
        )
    if "page needs to be reloaded" in low or "failed to extract any player response" in low:
        return (
            "YouTube tạm chặn truy cập từ máy chủ (thử thách bảo vệ bot). "
            "Vui lòng thử lại sau ít phút, hoặc dùng link nguồn khác / tải lên file âm thanh."
        )
    if "age" in low and ("restricted" in low or "confirm your age" in low):
        return "Video này bị giới hạn độ tuổi và yêu cầu đăng nhập để xác nhận."
    if "private video" in low:
        return "Video YouTube này ở chế độ riêng tư (private), không thể truy cập."
    if "video unavailable" in low or "removed by the uploader" in low:
        return "Video YouTube này không khả dụng hoặc đã bị xóa."
    if "live event will begin" in low or "is live" in low:
        return "Không hỗ trợ xử lý luồng phát trực tiếp (Live Stream)."
    if "not a valid url" in low or "unsupported url" in low:
        return f"Đường dẫn YouTube không đúng định dạng: {url}"
    return f"Không thể tải video YouTube: {err_msg}"


class YouTubeService:
    """Xử lý trích xuất âm thanh từ YouTube bằng yt-dlp (đa chiến lược client)."""

    @classmethod
    def _build_ydl_opts(cls, client_strategy: Optional[List[str]]) -> Dict[str, Any]:
        """Xây dựng cấu hình yt-dlp cho một chiến lược client cụ thể."""
        opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "socket_timeout": 30,
            "retries": 3,
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            # Tải đồng thời nhiều fragment (DASH) giúp rút ngắn thời gian tải
            "concurrent_fragment_downloads": 8,
            # JS runtime để giải n-challenge (yt-dlp-ejs)
            "js_runtimes": {"node": {}},
        }
        if client_strategy:
            opts["extractor_args"] = {"youtube": {"player_client": client_strategy}}

        # Cookies chỉ dùng cho các client web-family (bắt buộc cho IP datacenter
        # bị YouTube bot-check). KHÔNG đính cookies cho android family — client
        # này hoạt động ẩn danh và Google có thể khóa tài khoản nếu lạm dụng.
        strategy_id = client_strategy[0] if client_strategy else ""
        cookies_file = get_cookies_file()
        if cookies_file and strategy_id not in _NO_COOKIE_CLIENTS:
            opts["cookiefile"] = cookies_file
            logger.info("Sử dụng YouTube cookies từ: %s", cookies_file)
        return opts

    @classmethod
    def _extract_info_safe(
        cls,
        url: str,
        download: bool,
        target_dir: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], int]:
        """
        Thử extract_info lần lượt theo các chiến lược client (ANDROID trước).
        Trả về (info_dict, chỉ_số_chiến_lược_thành_công).
        """
        last_err: Exception = RuntimeError("Unknown YouTube error")
        for idx, strategy in enumerate(CLIENT_STRATEGIES):
            label = _STRATEGY_LABELS.get(idx, str(strategy))
            opts = cls._build_ydl_opts(strategy)
            if target_dir:
                opts["outtmpl"] = os.path.join(target_dir, "yt_%(id)s.%(ext)s")
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=download)
                if info is None:
                    raise RuntimeError("yt-dlp không trả về dữ liệu video.")
                logger.info("Tải YouTube OK với client %s", label)
                return info, idx
            except yt_dlp.utils.DownloadError as err:
                last_err = err
                logger.warning("Client %s thất bại: %s", label, err)
            except Exception as err:  # noqa: BLE001
                last_err = err
                logger.warning("Client %s thất bại (lỗi khác): %s", label, err)
        raise RuntimeError(_friendly_yt_error(str(last_err), url))

    @classmethod
    def _sync_download(cls, url: str, target_dir: str) -> Tuple[str, Dict[str, Any]]:
        """
        Tiến trình đồng bộ tải và chuẩn hóa âm thanh YouTube.
        Chạy trong asyncio.to_thread để không làm nghẽn Event Loop.
        """
        logger.info("Đang tải YouTube qua yt-dlp: %s", url)

        # 1. Tải audio với đa chiến lược client (tự retry theo từng client)
        info, _strategy_idx = cls._extract_info_safe(url, download=True, target_dir=target_dir)

        # 2. Kiểm tra thời lượng
        duration = info.get("duration")
        if duration and duration > MAX_AUDIO_DURATION_SECONDS:
            max_mins = MAX_AUDIO_DURATION_SECONDS // 60
            raise ValueError(
                f"Thời lượng tác phẩm ({int(duration)} giây) vượt quá giới hạn cho phép ({max_mins} phút)."
            )

        title = info.get("title") or "YouTube Audio"
        safe_title = sanitize_filename(title)

        # 3. Xác định file đã tải về (yt-dlp đã merge/convert theo format)
        downloaded = None
        req = info.get("requested_downloads") or []
        if req:
            downloaded = req[0].get("filepath") or req[0].get("filename")
        if not downloaded:
            # Fallback: tìm file mới nhất trong target_dir có id video
            vid = info.get("id", "")
            candidates = [
                os.path.join(target_dir, f) for f in os.listdir(target_dir)
                if vid and vid in f
            ]
            if candidates:
                downloaded = max(candidates, key=os.path.getmtime)
        if not downloaded or not os.path.exists(downloaded):
            raise RuntimeError("yt-dlp tải xong nhưng không tìm thấy file âm thanh trên đĩa.")

        # 4. Chuẩn hóa sang WAV PCM 44.1kHz (model Transkun dùng fs=44100,
        #    WAV PCM tránh mất chất lượng qua encode MP3 trung gian)
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

        # 5. Backup cookies sau lần tải thành công (yt-dlp đã ghi ngược cookie xoay)
        _backup_cookies()

        metadata = {
            "title": title,
            "duration": duration,
            "uploader": info.get("uploader") or "YouTube",
            "thumbnail": info.get("thumbnail"),
            "webpage_url": info.get("webpage_url") or url,
        }

        logger.info("Tải thành công từ YouTube: %s (File: %s)", title, output_file)
        return output_file, metadata

    @classmethod
    async def download(cls, url: str, target_dir: str) -> Tuple[str, Dict[str, Any]]:
        """
        Tải âm thanh bất đồng bộ từ liên kết YouTube.

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
