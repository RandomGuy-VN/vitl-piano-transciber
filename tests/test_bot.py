"""
Bộ kiểm thử đơn vị và tích hợp (Unit & Integration Tests) cho Vitl Piano Bot.
Kiểm tra các hàm tiện ích, cấu hình, Embed Builder, AudioFetcher, TranskunService, QueueManager,
HealthCheckServer, YouTubeService, SpotifyService, StyleService và Cogs.
"""

import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import discord

from config import (
    get_device_info,
    check_system_dependencies,
    MAX_FILE_SIZE_MB,
    MAX_AUDIO_DURATION_SECONDS,
    SUPPORTED_AUDIO_EXTENSIONS,
)
from utils.helpers import (
    format_bytes,
    format_duration,
    format_elapsed_time,
    sanitize_filename,
    is_spotify_url,
    is_youtube_url,
    is_valid_url,
    detect_source_name,
)
from services.embed_builder import EmbedBuilder
from services.transkun_service import TranskunService, TranscriptionResult
from services.audio_fetcher import AudioFetcher, AudioSourceInfo
from services.queue_manager import QueueManager
from services.health_server import HealthCheckServer
from services.youtube_service import YouTubeService
from services.spotify_service import SpotifyService
from services.direct_download_service import DirectDownloadService
from services.style_service import (
    hex_to_decimal,
    parse_hex_colors,
    update_bot_name_style,
    resolve_font_id,
    resolve_effect_id,
)
from cogs.transcription import TranscriptionCog
from cogs.style import StyleCog


class TestHelpers(unittest.TestCase):
    """Kiểm tra các hàm trong utils/helpers.py"""

    def test_format_bytes(self):
        self.assertEqual(format_bytes(500), "500.00 B")
        self.assertEqual(format_bytes(1024), "1.00 KB")
        self.assertEqual(format_bytes(1024 * 1024 * 2.5), "2.50 MB")
        self.assertEqual(format_bytes(-10), "0 B")

    def test_format_duration(self):
        self.assertEqual(format_duration(45), "00:45")
        self.assertEqual(format_duration(125), "02:05")
        self.assertEqual(format_duration(3665), "01:01:05")
        self.assertEqual(format_duration(None), "Không rõ")
        self.assertEqual(format_duration(-5), "Không rõ")

    def test_format_elapsed_time(self):
        self.assertEqual(format_elapsed_time(12.34), "12.3s")
        self.assertEqual(format_elapsed_time(85.2), "1m 25.2s")
        self.assertEqual(format_elapsed_time(-1), "0.0s")

    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename("Chopin: Nocturne Op. 9 No. 2?"), "Chopin Nocturne Op. 9 No. 2")
        self.assertEqual(sanitize_filename("A" * 100, max_length=50), "A" * 50)
        self.assertEqual(sanitize_filename("   "), "transcription")

    def test_is_spotify_url(self):
        self.assertTrue(is_spotify_url("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT"))
        self.assertTrue(is_spotify_url("https://spotify.link/AbCdEf123"))
        self.assertFalse(is_spotify_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertFalse(is_spotify_url(""))

    def test_is_youtube_url(self):
        self.assertTrue(is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertTrue(is_youtube_url("https://youtu.be/dQw4w9WgXcQ"))
        self.assertTrue(is_youtube_url("https://music.youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertFalse(is_youtube_url("https://open.spotify.com/track/123"))
        self.assertFalse(is_youtube_url(""))

    def test_is_valid_url(self):
        self.assertTrue(is_valid_url("https://example.com/audio.mp3"))
        self.assertTrue(is_valid_url("http://localhost:8080/song.wav"))
        self.assertFalse(is_valid_url("invalid-url"))
        self.assertFalse(is_valid_url("ftp://example.com"))
        self.assertFalse(is_valid_url(""))

    def test_detect_source_name(self):
        self.assertEqual(detect_source_name("https://youtu.be/test"), "YouTube")
        self.assertEqual(detect_source_name("https://www.youtube.com/watch?v=test"), "YouTube")
        self.assertEqual(detect_source_name("https://open.spotify.com/track/123"), "Spotify")
        self.assertEqual(detect_source_name("https://soundcloud.com/artist/song"), "SoundCloud")
        self.assertEqual(detect_source_name(""), "Tệp tải lên")


class TestEmbedBuilder(unittest.TestCase):
    """Kiểm tra các mẫu Embed trong services/embed_builder.py"""

    def test_create_queued_embed(self):
        embed = EmbedBuilder.create_queued_embed(
            source_label="Piano Track.mp3",
            source_type="Tệp đính kèm",
            queue_position=2,
            active_jobs=1
        )
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn("hàng chờ", embed.title)
        self.assertEqual(embed.color, EmbedBuilder.COLOR_QUEUED)

    def test_create_downloading_embed(self):
        embed = EmbedBuilder.create_downloading_embed(
            source_label="https://youtu.be/example",
            source_type="YouTube"
        )
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn("Đang tải âm thanh", embed.title)
        self.assertEqual(embed.color, EmbedBuilder.COLOR_DOWNLOADING)

    def test_create_processing_embed(self):
        embed = EmbedBuilder.create_processing_embed(
            title="Fur Elise",
            duration_sec=180,
            device_display_name="NVIDIA RTX 3050",
            is_cuda=True
        )
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn("Đang phân tích nốt", embed.title)
        self.assertEqual(embed.color, EmbedBuilder.COLOR_PROCESSING)

    def test_create_success_embed(self):
        embed = EmbedBuilder.create_success_embed(
            title="Moonlight Sonata",
            midi_size_bytes=15000,
            audio_duration_sec=300,
            elapsed_time_sec=14.5,
            device_display_name="NVIDIA RTX 3050"
        )
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn("Chuyển đổi thành công", embed.title)
        self.assertEqual(embed.color, EmbedBuilder.COLOR_SUCCESS)

    def test_create_error_embed(self):
        embed = EmbedBuilder.create_error_embed(
            error_title="Lỗi kết nối",
            error_description="Không thể tải video do bị chặn khu vực.",
            suggestion="Thử dùng một video khác."
        )
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn("Có lỗi xảy ra", embed.title)
        self.assertEqual(embed.color, EmbedBuilder.COLOR_ERROR)


class TestConfigAndDependencies(unittest.TestCase):
    """Kiểm tra cấu hình và kiểm tra phần cứng/công cụ"""

    def test_check_system_dependencies(self):
        deps = check_system_dependencies()
        self.assertIn("ffmpeg", deps)
        self.assertIn("ffprobe", deps)

    def test_get_device_info(self):
        device_flag, device_display, is_cuda = get_device_info()
        self.assertIn(device_flag, ["cuda", "cpu"])
        self.assertIsInstance(device_display, str)
        self.assertIsInstance(is_cuda, bool)


class TestStyleService(unittest.IsolatedAsyncioTestCase):
    """Kiểm tra dịch vụ cập nhật style tên bot (font, effect, colors)"""

    def test_hex_to_decimal(self):
        self.assertEqual(hex_to_decimal("#5865F2"), 5793266)
        self.assertEqual(hex_to_decimal("FFFFFF"), 16777215)
        self.assertEqual(hex_to_decimal("#000000"), 0)
        self.assertEqual(hex_to_decimal("FFF"), 16777215)

        with self.assertRaises(ValueError):
            hex_to_decimal("not-a-hex")

    def test_parse_hex_colors(self):
        colors = parse_hex_colors("#5865F2, #EB459E, #FEE75C")
        self.assertEqual(len(colors), 3)
        self.assertEqual(colors[0], hex_to_decimal("#5865F2"))

        # Test tối đa 4 màu
        colors_5 = parse_hex_colors("#111111, #222222, #333333, #444444, #555555")
        self.assertEqual(len(colors_5), 4)

        # Test default fallback
        default_colors = parse_hex_colors(None)
        self.assertGreaterEqual(len(default_colors), 1)

    def test_resolve_font_and_effect_id(self):
        # Numeric
        self.assertEqual(resolve_font_id(5), 5)
        self.assertEqual(resolve_font_id(99), 12)
        self.assertEqual(resolve_font_id(-1), 1)

        # String aliases
        self.assertEqual(resolve_font_id("monospace"), 5)
        self.assertEqual(resolve_font_id("gothic"), 2)
        self.assertEqual(resolve_font_id("cursive"), 3)
        self.assertEqual(resolve_font_id("bold"), 4)
        self.assertEqual(resolve_font_id("unknown"), 1)

        # Effect resolver
        self.assertEqual(resolve_effect_id(2), 2)
        self.assertEqual(resolve_effect_id("neon"), 2)
        self.assertEqual(resolve_effect_id("gradient"), 3)
        self.assertEqual(resolve_effect_id("glitch"), 6)
        self.assertEqual(resolve_effect_id("invalid"), 1)

    async def test_update_bot_name_style_no_token(self):
        with self.assertRaises(ValueError):
            await update_bot_name_style(guild_id=123, bot_token="")


class TestAudioFetcher(unittest.IsolatedAsyncioTestCase):
    """Kiểm tra các hàm xác thực và tải âm thanh trong AudioFetcher"""

    async def test_fetch_attachment_invalid_extension(self):
        mock_attachment = MagicMock(spec=discord.Attachment)
        mock_attachment.filename = "document.pdf"
        mock_attachment.size = 1024 * 1024

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(ValueError) as ctx:
                await AudioFetcher.fetch_attachment(mock_attachment, tmpdir)
            self.assertIn("không được hỗ trợ", str(ctx.exception))

    async def test_fetch_attachment_file_too_large(self):
        mock_attachment = MagicMock(spec=discord.Attachment)
        mock_attachment.filename = "huge_piano.mp3"
        mock_attachment.size = (MAX_FILE_SIZE_MB + 10) * 1024 * 1024

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(ValueError) as ctx:
                await AudioFetcher.fetch_attachment(mock_attachment, tmpdir)
            self.assertIn("vượt quá giới hạn cho phép", str(ctx.exception))

    async def test_fetch_url_invalid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(ValueError) as ctx:
                await AudioFetcher.fetch_url("invalid://not-a-link", tmpdir)
            self.assertIn("không hợp lệ", str(ctx.exception))

    async def test_fetch_attachment_success(self):
        mock_attachment = MagicMock(spec=discord.Attachment)
        mock_attachment.filename = "test_song.mp3"
        mock_attachment.size = 1024 * 500
        mock_attachment.save = AsyncMock()

        with tempfile.TemporaryDirectory() as tmpdir:
            info = await AudioFetcher.fetch_attachment(mock_attachment, tmpdir)
            self.assertEqual(info.title, "test_song.mp3")
            self.assertEqual(info.source_type, "Tệp tải lên")
            mock_attachment.save.assert_awaited_once()


class TestQueueManager(unittest.IsolatedAsyncioTestCase):
    """Kiểm tra dịch vụ quản lý hàng đợi QueueManager trên Cloud"""

    async def test_queue_acquire_and_release(self):
        qm = QueueManager()
        self.assertEqual(qm.active_jobs, 0)

        async with qm.acquire_slot() as queue_pos:
            self.assertEqual(qm.active_jobs, 1)

        self.assertEqual(qm.active_jobs, 0)


class TestHealthServer(unittest.TestCase):
    """Kiểm tra máy chủ Web Health Check"""

    def test_health_server_init(self):
        mock_bot = MagicMock(spec=discord.Client)
        mock_bot.user = None
        mock_bot.latency = 0.05
        mock_bot.guilds = []
        server = HealthCheckServer(mock_bot, port=9999)
        self.assertEqual(server.port, 9999)
        self.assertGreaterEqual(server._get_memory_usage_mb(), 0)


class TestTranskunService(unittest.IsolatedAsyncioTestCase):
    """Kiểm tra dịch vụ AI Transkun"""

    async def test_transcribe_file_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(FileNotFoundError):
                await TranskunService.transcribe(
                    audio_path="/non/existent/path.mp3",
                    title="Non Existent",
                    target_dir=tmpdir
                )

    @patch.object(TranskunService, "_execute_transcription")
    async def test_transcribe_success(self, mock_exec):
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, "input.mp3")
            with open(audio_path, "wb") as f:
                f.write(b"fake audio bytes")

            output_mid = os.path.join(tmpdir, "Test Song.mid")

            async def side_effect(in_path, out_path, dev):
                with open(out_path, "wb") as f:
                    f.write(b"MThd" + b"\x00" * 100)
                return 0, "Transkun finished successfully", ""

            mock_exec.side_effect = side_effect

            result = await TranskunService.transcribe(
                audio_path=audio_path,
                title="Test Song",
                target_dir=tmpdir,
                audio_duration_sec=120.0
            )

            self.assertIsInstance(result, TranscriptionResult)
            self.assertEqual(result.midi_path, output_mid)
            self.assertGreater(result.midi_size_bytes, 0)
            self.assertEqual(result.audio_duration_sec, 120.0)


class TestTranscriptionCog(unittest.IsolatedAsyncioTestCase):
    """Kiểm tra Cog /transcript và quy trình xác thực tham số"""

    async def test_transcript_no_args_shows_error(self):
        bot = MagicMock()
        cog = TranscriptionCog(bot)

        mock_interaction = MagicMock(spec=discord.Interaction)
        mock_interaction.response.send_message = AsyncMock()

        await cog.transcript.callback(cog, mock_interaction, url=None, file=None)
        mock_interaction.response.send_message.assert_awaited_once()
        _, kwargs = mock_interaction.response.send_message.call_args
        self.assertIn("embed", kwargs)
        self.assertEqual(kwargs["embed"].color, EmbedBuilder.COLOR_ERROR)


class TestStyleCog(unittest.IsolatedAsyncioTestCase):
    """Kiểm tra Cog /setstyle và kiểm tra quyền hạn admin"""

    async def test_setstyle_unauthorized_user(self):
        bot = MagicMock()
        bot.is_owner = AsyncMock(return_value=False)
        cog = StyleCog(bot)

        mock_user = MagicMock(spec=discord.Member)
        mock_user.guild_permissions.administrator = False

        mock_interaction = MagicMock(spec=discord.Interaction)
        mock_interaction.user = mock_user
        mock_interaction.guild = MagicMock()
        mock_interaction.response.send_message = AsyncMock()

        await cog.set_style.callback(cog, mock_interaction, font_id=1, effect_id=1, colors="#5865F2")
        mock_interaction.response.send_message.assert_awaited_once()
        _, kwargs = mock_interaction.response.send_message.call_args
        self.assertIn("embed", kwargs)
        self.assertIn("Không có quyền", kwargs["embed"].title)


if __name__ == "__main__":
    unittest.main()
