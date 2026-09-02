"""
Quản lý hàng đợi và giới hạn số lượng tác vụ AI chạy đồng thời trên môi trường Cloud.
Ngăn chặn hiện tượng Out-Of-Memory (OOM Kill) và nghẽn CPU khi nhiều người dùng gửi yêu cầu cùng lúc.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from config import MAX_CONCURRENT_JOBS

logger = logging.getLogger(__name__)


class QueueManager:
    """Quản trị viên điều phối hàng đợi tác vụ AI Transcription."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)
            cls._instance._active_jobs = 0
            cls._instance._waiting_jobs = 0
            cls._instance._lock = asyncio.Lock()
        return cls._instance

    @property
    def active_jobs(self) -> int:
        """Số tác vụ AI đang thực thi cùng lúc."""
        return self._active_jobs

    @property
    def waiting_jobs(self) -> int:
        """Số tác vụ đang nằm trong hàng chờ."""
        return self._waiting_jobs

    @asynccontextmanager
    async def acquire_slot(self) -> AsyncGenerator[int, None]:
        """
        Context manager để xin cấp phát slot xử lý AI.
        
        Yields:
            int: Vị trí hàng chờ khi bắt đầu chờ (0 nếu được chạy ngay lập tức, >=1 nếu phải chờ).
        """
        async with self._lock:
            if self._semaphore.locked():
                self._waiting_jobs += 1
                queue_position = self._waiting_jobs
            else:
                queue_position = 0

        logger.debug("Tác vụ mới vào hàng chờ. Vị trí ban đầu: %d", queue_position)

        try:
            # Chờ đến khi có slot trống
            await self._semaphore.acquire()

            async with self._lock:
                if queue_position > 0:
                    self._waiting_jobs = max(0, self._waiting_jobs - 1)
                self._active_jobs += 1

            logger.info("Tác vụ đã nhận được slot AI. Đang chạy: %d/%d", self._active_jobs, MAX_CONCURRENT_JOBS)
            yield queue_position

        finally:
            async with self._lock:
                self._active_jobs = max(0, self._active_jobs - 1)
            self._semaphore.release()
            logger.debug("Tác vụ đã giải phóng slot AI. Đang chạy: %d/%d", self._active_jobs, MAX_CONCURRENT_JOBS)


# Đối tượng hàng đợi Singleton dùng chung toàn hệ thống
job_queue = QueueManager()
