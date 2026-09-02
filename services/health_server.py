"""
Web Server báo trạng thái (Health Check) tích hợp cho các nền tảng Cloud (Railway, Render, Fly.io, Koyeb, K8s).
Cung cấp endpoint HTTP để Cloud PaaS kiểm tra liveness/readiness probe và tránh việc container bị shutdown.
"""

import asyncio
import logging
import os
import time
from typing import Optional
import aiohttp
from aiohttp import web
import discord

from config import PORT, get_device_info
from services.queue_manager import job_queue

logger = logging.getLogger(__name__)


class HealthCheckServer:
    """Máy chủ HTTP nhẹ báo cáo tình trạng hoạt động của Bot."""

    def __init__(self, bot: discord.Client, port: int = PORT) -> None:
        self.bot = bot
        self.port = port
        self.start_time = time.time()
        self.app = web.Application()
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Đăng ký các route cho Web Server."""
        self.app.router.add_get("/", self._handle_root)
        self.app.router.add_get("/health", self._handle_health)
        self.app.router.add_get("/status", self._handle_health)
        self.app.router.add_get("/ping", self._handle_ping)

    def _get_memory_usage_mb(self) -> float:
        """Lấy dung lượng RAM tiến trình đang sử dụng (MB)."""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return round(process.memory_info().rss / (1024 * 1024), 2)
        except Exception:
            return 0.0

    async def _handle_root(self, request: web.Request) -> web.Response:
        """Trang chủ hiển thị thông tin tổng quan."""
        uptime = int(time.time() - self.start_time)
        hours, rem = divmod(uptime, 3600)
        minutes, seconds = divmod(rem, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        bot_name = str(self.bot.user) if self.bot.user else "Đang kết nối..."
        latency = round(self.bot.latency * 1000, 2) if self.bot.latency else 0.0
        _, device_display, _ = get_device_info()

        html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vitl Piano Bot - Cloud Status</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0f172a;
            color: #f8fafc;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
        }}
        .card {{
            background: #1e293b;
            border-radius: 16px;
            padding: 32px;
            max-width: 500px;
            width: 90%;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            border: 1px solid #334155;
        }}
        h1 {{ margin-top: 0; color: #38bdf8; font-size: 24px; display: flex; align-items: center; gap: 10px; }}
        .badge {{ background: #22c55e; color: #000; padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: bold; }}
        .item {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #334155; font-size: 14px; }}
        .item:last-child {{ border-bottom: none; }}
        .label {{ color: #94a3b8; }}
        .value {{ font-weight: 600; color: #f1f5f9; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>🎹 Vitl Piano Bot <span class="badge">ONLINE</span></h1>
        <div class="item"><span class="label">Tên Bot</span><span class="value">{bot_name}</span></div>
        <div class="item"><span class="label">Độ trễ Discord (Latency)</span><span class="value">{latency} ms</span></div>
        <div class="item"><span class="label">Thời gian hoạt động (Uptime)</span><span class="value">{uptime_str}</span></div>
        <div class="item"><span class="label">Số máy chủ (Guilds)</span><span class="value">{len(self.bot.guilds)}</span></div>
        <div class="item"><span class="label">Thiết bị AI</span><span class="value">{device_display}</span></div>
        <div class="item"><span class="label">Tác vụ AI đang chạy</span><span class="value">{job_queue.active_jobs}</span></div>
        <div class="item"><span class="label">Tác vụ trong hàng chờ</span><span class="value">{job_queue.waiting_jobs}</span></div>
        <div class="item"><span class="label">Bộ nhớ RAM</span><span class="value">{self._get_memory_usage_mb()} MB</span></div>
    </div>
</body>
</html>"""
        return web.Response(text=html_content, content_type="text/html")

    async def _handle_health(self, request: web.Request) -> web.Response:
        """Endpoint JSON báo cáo sức khỏe (Health Check probe)."""
        is_ready = self.bot.is_ready()
        status_str = "healthy" if is_ready else "starting"
        _, device_display, is_cuda = get_device_info()

        data = {
            "status": status_str,
            "bot_ready": is_ready,
            "bot_user": str(self.bot.user) if self.bot.user else None,
            "latency_ms": round(self.bot.latency * 1000, 2) if self.bot.latency else 0.0,
            "uptime_seconds": round(time.time() - self.start_time, 1),
            "guilds_count": len(self.bot.guilds),
            "device": device_display,
            "is_cuda": is_cuda,
            "queue": {
                "active_jobs": job_queue.active_jobs,
                "waiting_jobs": job_queue.waiting_jobs,
            },
            "memory_usage_mb": self._get_memory_usage_mb(),
        }

        status_code = 200 if is_ready else 503
        return web.json_response(data, status=status_code)

    async def _handle_ping(self, request: web.Request) -> web.Response:
        """Endpoint ping nhanh trả về pong."""
        return web.Response(text="pong", content_type="text/plain")

    async def start(self) -> None:
        """Khởi chạy HTTP Server bất đồng bộ."""
        self._runner = web.AppRunner(self.app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, "0.0.0.0", self.port)
        await self._site.start()
        logger.info("-> Khởi chạy Cloud Health Server thành công trên cổng http://0.0.0.0:%d", self.port)

    async def stop(self) -> None:
        """Dừng HTTP Server an toàn khi Bot tắt."""
        if self._runner:
            await self._runner.cleanup()
            logger.info("-> Đã dừng Cloud Health Server an toàn.")
