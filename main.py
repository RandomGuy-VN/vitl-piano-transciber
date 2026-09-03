"""
Điểm khởi chạy chính (Entrypoint) cho Vitl Piano Discord Bot.
Tối ưu hóa cho môi trường Cloud & GitHub Actions với Web Health Server, Preload AI weights,
tự động đồng bộ Style Tên Bot (Font, Effect, Gradient), bảo vệ đồng bộ Slash Commands chống lỗi 403 Missing Access
và quản lý Graceful Shutdown.
"""

import asyncio
import os
import signal
import sys
import logging
import discord
from discord.ext import commands

from config import (
    DISCORD_BOT_TOKEN,
    TARGET_GUILD_ID,
    PORT,
    ENABLE_HEALTH_SERVER,
    PRELOAD_MODEL_ON_STARTUP,
    ENABLE_AUTO_STYLE,
    DEFAULT_FONT_ID,
    DEFAULT_EFFECT_ID,
    DEFAULT_HEX_COLORS,
    get_device_info,
    check_system_dependencies,
)
from services.health_server import HealthCheckServer
from services.model_manager import ModelManager
from services.style_service import update_bot_name_style
from utils.logger import setup_logger

# Khởi tạo hệ thống log
logger = setup_logger("vitl_piano_bot", level=logging.INFO)


class VitlPianoBot(commands.Bot):
    """Lớp Bot tùy chỉnh kế thừa từ commands.Bot của discord.py v2.x."""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
        self.health_server: HealthCheckServer | None = None

    async def setup_hook(self) -> None:
        """Nạp các extension Cogs, khởi động Web Health Check và đồng bộ hóa slash command."""
        # 1. Khởi động Web Server báo trạng thái cho Cloud PaaS
        if ENABLE_HEALTH_SERVER:
            try:
                self.health_server = HealthCheckServer(self, port=PORT)
                await self.health_server.start()
            except Exception as hs_err:
                logger.warning("Không thể khởi động Web Health Server trên cổng %d: %s", PORT, hs_err)

        # 2. Nạp Cogs
        logger.info("Đang nạp các module Cogs...")
        cogs_to_load = ["cogs.transcription", "cogs.style"]
        for cog_name in cogs_to_load:
            try:
                await self.load_extension(cog_name)
                logger.info("-> Nạp thành công module: %s", cog_name)
            except Exception as exc:
                logger.exception("-> Không thể nạp module %s: %s", cog_name, exc)

        # 3. Đồng bộ lệnh Slash Command (với cơ chế tự động Fallback & Bắt lỗi an toàn)
        try:
            if TARGET_GUILD_ID:
                try:
                    guild = discord.Object(id=TARGET_GUILD_ID)
                    self.tree.copy_global_to(guild=guild)
                    synced = await self.tree.sync(guild=guild)
                    logger.info(
                        "Đã đồng bộ %d Slash Commands tới Guild ID: %d (Có hiệu lực ngay lập tức)",
                        len(synced),
                        TARGET_GUILD_ID
                    )
                except discord.Forbidden as f_err:
                    logger.warning(
                        "⚠️ Không thể đồng bộ lệnh tới Guild ID %d do thiếu quyền (403 Forbidden: Missing Access).\n"
                        "Nguyên nhân: Bot chưa được mời vào Server này hoặc link mời thiếu scope 'applications.commands'.\n"
                        "-> Đang tự động chuyển sang Đồng bộ Toàn cầu (Global Sync)...",
                        TARGET_GUILD_ID
                    )
                    synced = await self.tree.sync()
                    logger.info("Đã đồng bộ %d Slash Commands toàn cầu (Global Sync)", len(synced))
                except discord.HTTPException as http_err:
                    logger.warning("Lỗi HTTP khi đồng bộ Guild ID %d (%s). Thử lại với Global Sync...", TARGET_GUILD_ID, http_err)
                    synced = await self.tree.sync()
                    logger.info("Đã đồng bộ %d Slash Commands toàn cầu (Global Sync)", len(synced))
            else:
                synced = await self.tree.sync()
                logger.info("Đã đồng bộ %d Slash Commands toàn cầu (Global Sync)", len(synced))
        except Exception as sync_err:
            logger.error("Lỗi khi đồng bộ Slash Commands: %s. Bot vẫn tiếp tục khởi động.", sync_err)

        # 4. Tự động kiểm tra và nạp trước model weights chạy nền nếu được bật
        if PRELOAD_MODEL_ON_STARTUP:
            asyncio.create_task(ModelManager.preload_and_warmup())

    async def close(self) -> None:
        """Dừng Bot và giải phóng các tài nguyên HTTP Server an toàn."""
        logger.info("Đang tiến hành tắt Bot và giải phóng tài nguyên...")
        if self.health_server:
            try:
                await self.health_server.stop()
            except Exception as e:
                logger.warning("Lỗi khi dừng health server: %s", e)
        await super().close()

    async def on_ready(self) -> None:
        """Xử lý khi Bot đã kết nối thành công và sẵn sàng hoạt động."""
        logger.info("=" * 60)
        logger.info("   🎹 VITL PIANO BOT ĐÃ SẴN SÀNG HOẠT ĐỘNG (ONLINE) 🎹")
        logger.info("=" * 60)
        logger.info("Tên Bot       : %s (ID: %s)", self.user.name, self.user.id)
        logger.info("Số Guilds     : %d", len(self.guilds))

        # In danh sách Server Bot đang tham gia
        if self.guilds:
            logger.info("Danh sách Servers:")
            for g in self.guilds:
                logger.info(" - %s (ID: %d)", g.name, g.id)
        else:
            logger.warning("⚠️ Bot hiện chưa ở trong bất kỳ Server Discord nào! Hãy mời Bot vào Server để sử dụng.")

        # Kiểm tra phần cứng
        device_flag, device_display, is_cuda = get_device_info()
        logger.info("Thiết bị AI   : %s [Flag: %s, CUDA: %s]", device_display, device_flag, is_cuda)

        # Kiểm tra công cụ hệ thống
        deps = check_system_dependencies()
        for dep, installed in deps.items():
            status_str = "✅ Đã cài đặt" if installed else "⚠️ Chưa tìm thấy"
            logger.info("Công cụ %-6s: %s", dep, status_str)

        # Cài đặt trạng thái hiện diện (Presence)
        activity = discord.Activity(
            type=discord.ActivityType.listening,
            name="/transcript | Piano to MIDI"
        )
        await self.change_presence(status=discord.Status.online, activity=activity)

        # 5. Tự động áp dụng Style Tên Bot (Font, Effect, Gradient) khi khởi động nếu được bật
        if ENABLE_AUTO_STYLE and self.guilds:
            logger.info("Đang tự động áp dụng Style Tên Bot (Font: %d, Effect: %d, Colors: %s)...",
                        DEFAULT_FONT_ID, DEFAULT_EFFECT_ID, DEFAULT_HEX_COLORS)
            try:
                # Chờ 1 giây để gateway ổn định kết nối
                await asyncio.sleep(1.0)
                style_res = await update_bot_name_style(
                    bot=self,
                    font_id=DEFAULT_FONT_ID,
                    effect_id=DEFAULT_EFFECT_ID,
                    hex_colors=DEFAULT_HEX_COLORS
                )
                if style_res.get("success"):
                    logger.info("-> Tự động cập nhật Style Tên Bot thành công trên %d/%d servers!",
                                style_res.get("updated_count", 0), style_res.get("total_guilds", 0))
                else:
                    logger.warning("-> Tự động cập nhật Style Tên Bot chưa hoàn tất: %s", style_res.get("details", ""))
            except Exception as style_err:
                logger.warning("Không thể tự động áp dụng Style Tên Bot trong on_ready: %s", style_err)

        logger.info("=" * 60)


def main() -> None:
    """Hàm khởi động chương trình chính."""
    if not DISCORD_BOT_TOKEN:
        logger.critical(
            "LỖI: Chưa tìm thấy biến môi trường DISCORD_BOT_TOKEN!\n"
            "Vui lòng cấu hình biến môi trường DISCORD_BOT_TOKEN trên GitHub Secrets hoặc file `.env`."
        )
        sys.exit(1)

    bot = VitlPianoBot()

    try:
        bot.run(DISCORD_BOT_TOKEN, log_handler=None)
    except discord.LoginFailure:
        logger.critical("LỖI: Token Discord không hợp lệ. Vui lòng kiểm tra lại DISCORD_BOT_TOKEN.")
        sys.exit(1)
    except Exception as exc:
        logger.exception("Lỗi không mong muốn khi chạy bot: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
