"""
Cấu hình hệ thống ghi log (Logging) chuyên nghiệp cho Vitl Piano Bot.
Hỗ trợ hiển thị màu sắc và định dạng thời gian trực quan trên console và ghi log ra file.
"""

import logging
import sys
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Bộ định dạng log với màu sắc theo cấp độ log trên Terminal."""

    # ANSI escape sequences
    GREY = "\x1b[38;20m"
    CYAN = "\x1b[36;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"

    FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"

    FORMATS = {
        logging.DEBUG: GREY + FORMAT + RESET,
        logging.INFO: CYAN + FORMAT + RESET,
        logging.WARNING: YELLOW + FORMAT + RESET,
        logging.ERROR: RED + FORMAT + RESET,
        logging.CRITICAL: BOLD_RED + FORMAT + RESET,
    }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno, self.FORMAT)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def setup_logger(
    name: str = "vitl_piano_bot",
    level: int = logging.INFO,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Khởi tạo và cấu hình Logger cho bot.

    Args:
        name (str): Tên của logger.
        level (int): Cấp độ log (mặc định logging.INFO).
        log_file (Optional[str]): Đường dẫn file để ghi log (nếu cần).

    Returns:
        logging.Logger: Đối tượng logger đã cấu hình.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Tránh gắn handler nhiều lần nếu hàm được gọi lại
    if logger.handlers:
        return logger

    # Console Handler với ColoredFormatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)

    # File Handler (nếu có cấu hình log_file)
    if log_file:
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger
