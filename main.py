"""
Điểm khởi chạy chính (Entrypoint) cho Vitl Piano Discord Bot.
Tối ưu hóa cho môi trường Cloud với Health Check HTTP Server, Preload AI weights và quản lý tín hiệu Graceful Shutdown.
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
    get_device_info,
    check_system_dependencies,
)
from services.health_server import HealthCheckServer
from services.model_manager import ModelManager
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
        try:
            await self.load_extension("cogs.transcription")
            logger.info("-> Nạp thành công module: cogs.transcription")
        except Exception as exc:
            logger.exception("-> Không thể nạp module cogs.transcription: %s", exc)

        # 3. Đồng bộ lệnh Slash Command
        if TARGET_GUILD_ID:
            guild = discord.Object(id=TARGET_GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logger.info("Đã đồng bộ %d Slash Commands tới Test Guild ID: %d (Có hiệu lực ngay lập tức)", len(synced), TARGET_GUILD_ID)
        else:
            synced = await self.tree.sync()
            logger.info("Đã đồng bộ %d Slash Commands toàn cầu (Global Sync)", len(synced))

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
        logger.info("   🎹 VITL PIANO BOT ĐÃ SẴN SÀNG HOẠT ĐỘNG (CLOUD READY) 🎹")
        logger.info("=" * 60)
        logger.info("Tên Bot       : %s (ID: %s)", self.user.name, self.user.id)
        logger.info("Số Guilds     : %d", len(self.guilds))

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
        logger.info("=" * 60)


def main() -> None:
    """Hàm khởi động chương trình chính."""
    if not DISCORD_BOT_TOKEN:
        logger.critical(
            "LỖI: Chưa tìm thấy biến môi trường DISCORD_BOT_TOKEN!\n"
            "Vui lòng cấu hình biến môi trường DISCORD_BOT_TOKEN trên Cloud Dashboard hoặc tạo file `.env`."
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
