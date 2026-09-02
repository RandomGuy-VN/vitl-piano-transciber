"""
Dịch vụ xử lý liên kết Spotify độc lập hoàn toàn, không phụ thuộc vào spotdl hay yt-dlp.
Trích xuất siêu dữ liệu qua Spotify oEmbed API và tải âm thanh độ phân giải cao qua pytubefix.
"""

import asyncio
import logging
import os
from typing import Dict, Any, Tuple
import aiohttp
from pytubefix import Search

from config import DOWNLOAD_TIMEOUT_SECONDS
from services.youtube_service import YouTubeService

logger = logging.getLogger(__name__)


class SpotifyService:
    """Xử lý tải âm thanh từ các bài hát Spotify mà không cần cài đặt spotdl hay yt-dlp."""

    @classmethod
    async def _fetch_spotify_metadata(cls, spotify_url: str) -> Dict[str, str]:
        """Lấy thông tin tiêu đề và nghệ sĩ từ Spotify oEmbed API (không yêu cầu API Key)."""
        oembed_endpoint = f"https://open.spotify.com/oembed?url={spotify_url}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(oembed_endpoint, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "title": data.get("title", ""),
                            "artist": data.get("author_name", ""),
                            "thumbnail": data.get("thumbnail_url", ""),
                        }
            except Exception as e:
                logger.warning("Không thể lấy Spotify oEmbed metadata: %s", e)
        return {}

    @classmethod
    def _search_youtube_top_match(cls, query: str) -> str:
        """Tìm kiếm video YouTube phù hợp nhất với tên bài hát."""
        logger.info("Đang tìm kiếm bài hát trên YouTube: %s", query)
        s = Search(query)
        if not s.videos:
            raise ValueError(f"Không tìm thấy bản âm thanh phù hợp trên YouTube cho bài hát: {query}")
        top_video = s.videos[0]
        return top_video.watch_url

    @classmethod
    async def download(cls, url: str, target_dir: str) -> Tuple[str, Dict[str, Any]]:
        """
        Tải bài hát từ liên kết Spotify về thư mục tạm.

        Args:
            url (str): Liên kết Spotify bài hát.
            target_dir (str): Thư mục lưu trữ tạm thời.

        Returns:
            Tuple[str, Dict[str, Any]]: (Đường dẫn file MP3, Dict metadata)
        """
        logger.info("Bắt đầu xử lý tải nhạc Spotify: %s", url)

        # 1. Lấy thông tin bài hát từ Spotify oEmbed
        meta = await cls._fetch_spotify_metadata(url)
        title = meta.get("title")
        artist = meta.get("artist")

        if title and artist:
            search_query = f"{artist} - {title} audio"
        elif title:
            search_query = f"{title} audio"
        else:
            # Fallback nếu oEmbed không lấy được
            clean_id = url.split("track/")[-1].split("?")[0]
            search_query = f"spotify track {clean_id}"

        # 2. Tìm kiếm video YouTube tương ứng qua pytubefix.Search
        try:
            matched_yt_url = await asyncio.wait_for(
                asyncio.to_thread(cls._search_youtube_top_match, search_query),
                timeout=DOWNLOAD_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Quá thời gian tìm kiếm bài hát Spotify ({DOWNLOAD_TIMEOUT_SECONDS}s).")

        logger.info("Tìm thấy liên kết đối ứng cho Spotify: %s -> %s", search_query, matched_yt_url)

        # 3. Tải âm thanh qua YouTubeService
        file_path, yt_meta = await YouTubeService.download(matched_yt_url, target_dir)

        # Cập nhật metadata với thông tin chuẩn từ Spotify nếu có
        result_metadata = {
            "title": f"{artist} - {title}" if (artist and title) else yt_meta.get("title", "Spotify Audio"),
            "duration": yt_meta.get("duration"),
            "uploader": artist or yt_meta.get("uploader", "Spotify"),
            "thumbnail": meta.get("thumbnail") or yt_meta.get("thumbnail"),
            "webpage_url": url,
        }

        return file_path, result_metadata
