"""
Module khởi tạo các tin nhắn trạng thái Embed chuẩn hóa và trực quan cho Discord Bot.
"""

from datetime import datetime
from typing import Optional
import discord

from utils.helpers import format_bytes, format_duration, format_elapsed_time


class EmbedBuilder:
    """Xây dựng các mẫu giao diện Discord Embed thông báo trạng thái."""

    # Bảng mã màu chuẩn Discord
    COLOR_QUEUED = discord.Color.orange()        # Màu cam (0xE67E22) - Trạng thái hàng chờ
    COLOR_DOWNLOADING = discord.Color.gold()      # Màu vàng (0xFEE75C / 0xF1C40F)
    COLOR_PROCESSING = discord.Color.blue()       # Màu xanh dương (0x3498DB / 0x5865F2)
    COLOR_SUCCESS = discord.Color.green()         # Màu xanh lá (0x2ECC71 / 0x57F287)
    COLOR_ERROR = discord.Color.red()             # Màu đỏ (0xED4245 / 0xE74C3C)

    FOOTER_TEXT = "Vitl Piano Bot • Powered by Transkun AI"

    @classmethod
    def create_queued_embed(
        cls,
        source_label: str,
        source_type: str,
        queue_position: int,
        active_jobs: int
    ) -> discord.Embed:
        """
        Embed Hàng chờ (Màu cam): Thông báo yêu cầu đang đợi slot AI trên Cloud.

        Args:
            source_label (str): Tên hiển thị nguồn dữ liệu.
            source_type (str): Phân loại nguồn (YouTube, Spotify, File đính kèm...).
            queue_position (int): Vị trí hàng chờ.
            active_jobs (int): Số tác vụ đang chạy.

        Returns:
            discord.Embed: Đối tượng Embed.
        """
        embed = discord.Embed(
            title="⏳ Yêu cầu đang nằm trong hàng chờ...",
            description="Hệ thống Cloud đang xử lý các tác vụ trước đó để tránh quá tải tài nguyên.",
            color=cls.COLOR_QUEUED,
            timestamp=datetime.now()
        )

        display_target = source_label if len(source_label) <= 60 else f"{source_label[:57]}..."
        embed.add_field(name="🎵 Yêu cầu của bạn", value=f"`{display_target}`", inline=False)
        embed.add_field(name="📍 Vị trí trong hàng chờ", value=f"**#{queue_position}**", inline=True)
        embed.add_field(name="⚙️ Tiến trình đang chạy", value=f"`{active_jobs} tác vụ`", inline=True)
        embed.add_field(
            name="ℹ️ Trạng thái",
            value="Bot sẽ tự động bắt đầu tải và chuyển đổi sang MIDI ngay khi đến lượt của bạn!",
            inline=False
        )

        embed.set_footer(text=cls.FOOTER_TEXT)
        return embed

    @classmethod
    def create_downloading_embed(
        cls,
        source_label: str,
        source_type: str,
        details: Optional[str] = None
    ) -> discord.Embed:
        """
        Embed 1: Thông báo đang tải âm thanh (Màu vàng).

        Args:
            source_label (str): Tên hiển thị (URL hoặc tên file đính kèm).
            source_type (str): Nguồn tải (YouTube, Spotify, SoundCloud, File đính kèm...).
            details (Optional[str]): Thông tin chi tiết bổ sung.

        Returns:
            discord.Embed: Đối tượng Embed được tạo.
        """
        embed = discord.Embed(
            title="📥 Đang tải âm thanh...",
            description="Đang tiến hành trích xuất và tối ưu hóa luồng âm thanh đầu vào.",
            color=cls.COLOR_DOWNLOADING,
            timestamp=datetime.now()
        )

        embed.add_field(name="🌐 Nguồn dữ liệu", value=f"`{source_type}`", inline=True)
        
        display_target = source_label if len(source_label) <= 60 else f"{source_label[:57]}..."
        embed.add_field(name="🎵 Đang xử lý", value=f"`{display_target}`", inline=True)

        if details:
            embed.add_field(name="ℹ️ Trạng thái", value=details, inline=False)
        else:
            embed.add_field(
                name="ℹ️ Trạng thái",
                value="⏳ Đang tải stream và chuyển đổi định dạng âm thanh (192kbps MP3)...",
                inline=False
            )

        embed.set_footer(text=cls.FOOTER_TEXT)
        return embed

    @classmethod
    def create_processing_embed(
        cls,
        title: str,
        duration_sec: Optional[float | int],
        device_display_name: str,
        is_cuda: bool
    ) -> discord.Embed:
        """
        Embed 2: Thông báo đang phân tích nốt và tạo MIDI (Màu xanh dương).

        Args:
            title (str): Tiêu đề bản nhạc/tên tệp.
            duration_sec (Optional[float | int]): Thời lượng âm thanh.
            device_display_name (str): Tên thiết bị phần cứng (GPU hoặc CPU).
            is_cuda (bool): True nếu chạy trên CUDA.

        Returns:
            discord.Embed: Đối tượng Embed được tạo.
        """
        embed = discord.Embed(
            title="🎹 Đang phân tích nốt & tạo MIDI...",
            description="Mô hình Transkun AI đang thực hiện nhận diện cao độ (pitch), phách và vận tốc phím (velocity).",
            color=cls.COLOR_PROCESSING,
            timestamp=datetime.now()
        )

        display_title = title if len(title) <= 60 else f"{title[:57]}..."
        embed.add_field(name="🎶 Tác phẩm", value=f"**{display_title}**", inline=False)
        embed.add_field(name="⏱️ Thời lượng", value=f"`{format_duration(duration_sec)}`", inline=True)
        
        hw_icon = "⚡ GPU Acceleration" if is_cuda else "🖥️ CPU Processing"
        embed.add_field(name="⚙️ Thiết bị phần cứng", value=f"`{device_display_name}`\n*({hw_icon})*", inline=True)

        embed.add_field(
            name="💡 Ghi chú",
            value="Quá trình này có thể mất từ vài giây đến một vài phút tùy thuộc vào độ dài bài hát và thiết bị xử lý.",
            inline=False
        )

        embed.set_footer(text=cls.FOOTER_TEXT)
        return embed

    @classmethod
    def create_success_embed(
        cls,
        title: str,
        midi_size_bytes: int,
        audio_duration_sec: Optional[float | int],
        elapsed_time_sec: float,
        device_display_name: str
    ) -> discord.Embed:
        """
        Embed 3: Thông báo chuyển đổi thành công (Màu xanh lá).

        Args:
            title (str): Tiêu đề tác phẩm.
            midi_size_bytes (int): Dung lượng file MIDI đã tạo.
            audio_duration_sec (Optional[float | int]): Thời lượng bài hát gốc.
            elapsed_time_sec (float): Thời gian bot xử lý xong.
            device_display_name (str): Thiết bị đã xử lý.

        Returns:
            discord.Embed: Đối tượng Embed được tạo.
        """
        embed = discord.Embed(
            title="✅ Chuyển đổi thành công!",
            description="File MIDI (.mid) của bản nhạc đã được khởi tạo hoàn tất. Bạn có thể tải file đính kèm bên dưới để mở trong Synthesia, MuseScore, FL Studio, Ableton hoặc bất kỳ DAW nào!",
            color=cls.COLOR_SUCCESS,
            timestamp=datetime.now()
        )

        display_title = title if len(title) <= 60 else f"{title[:57]}..."
        embed.add_field(name="🎼 Bản nhạc", value=f"**{display_title}**", inline=False)
        embed.add_field(name="⏱️ Thời lượng gốc", value=f"`{format_duration(audio_duration_sec)}`", inline=True)
        embed.add_field(name="📦 Dung lượng MIDI", value=f"`{format_bytes(midi_size_bytes)}`", inline=True)
        embed.add_field(name="⚡ Thời gian xử lý", value=f"`{format_elapsed_time(elapsed_time_sec)}`", inline=True)
        embed.add_field(name="🖥️ Thiết bị chạy", value=f"`{device_display_name}`", inline=True)

        embed.set_footer(text=f"{cls.FOOTER_TEXT} • Chúc bạn luyện tập vui vẻ!")
        return embed

    @classmethod
    def create_error_embed(
        cls,
        error_title: str,
        error_description: str,
        suggestion: Optional[str] = None
    ) -> discord.Embed:
        """
        Embed 4: Thông báo có lỗi xảy ra (Màu đỏ).

        Args:
            error_title (str): Tiêu đề ngắn gọn của lỗi.
            error_description (str): Chi tiết nguyên nhân xảy ra lỗi.
            suggestion (Optional[str]): Lời khuyên hoặc giải pháp khắc phục.

        Returns:
            discord.Embed: Đối tượng Embed được tạo.
        """
        embed = discord.Embed(
            title="❌ Có lỗi xảy ra",
            description=f"**{error_title}**",
            color=cls.COLOR_ERROR,
            timestamp=datetime.now()
        )

        # Cắt ngắn lỗi nếu quá dài vượt giới hạn Discord
        if len(error_description) > 1000:
            error_description = f"{error_description[:997]}..."

        embed.add_field(name="📝 Chi tiết lỗi", value=f"```{error_description}```", inline=False)

        if suggestion:
            embed.add_field(name="💡 Gợi ý khắc phục", value=suggestion, inline=False)

        embed.set_footer(text=cls.FOOTER_TEXT)
        return embed
