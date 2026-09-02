"""
Dịch vụ xử lý AI Transcription: Chuyển đổi file âm thanh sang định dạng MIDI bằng Transkun.
Hỗ trợ tăng tốc GPU CUDA, tối ưu CPU đa luồng trên Cloud và tự động dọn dẹp RAM/VRAM.
"""

import asyncio
import gc
import logging
import os
import shutil
import sys
import time
from dataclasses import dataclass
from typing import Optional

from config import (
    TRANSCRIPTION_TIMEOUT_SECONDS,
    CPU_THREADS,
    get_device_info,
)
from utils.helpers import sanitize_filename

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Kết quả hoàn tất sau quá trình AI Transcription."""
    midi_path: str
    midi_size_bytes: int
    audio_duration_sec: Optional[float]
    elapsed_time_sec: float
    device_display_name: str
    is_cuda: bool


class TranskunService:
    """Xử lý chuyển đổi âm thanh piano sang MIDI thông qua mô hình Transkun."""

    @staticmethod
    def _find_transkun_command() -> list[str]:
        """Xác định cách thức gọi lệnh Transkun tốt nhất trong môi trường hiện tại."""
        transkun_bin = shutil.which("transkun")
        if transkun_bin:
            return [transkun_bin]
        return [sys.executable, "-m", "transkun.transcribe"]

    @classmethod
    async def _execute_transcription(
        cls,
        audio_path: str,
        output_midi_path: str,
        device_flag: str
    ) -> tuple[int, str, str]:
        """Thực thi tiến trình Transkun qua subprocess bất đồng bộ."""
        base_cmd = cls._find_transkun_command()
        cmd = base_cmd + [audio_path, output_midi_path, "--device", device_flag]

        logger.info("Thực thi Transkun CLI: %s", " ".join(cmd))

        # Tối ưu hóa số luồng CPU cho Cloud instance nếu được cấu hình
        env = os.environ.copy()
        if CPU_THREADS > 0:
            env["OMP_NUM_THREADS"] = str(CPU_THREADS)
            env["MKL_NUM_THREADS"] = str(CPU_THREADS)
            env["TORCH_NUM_THREADS"] = str(CPU_THREADS)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=TRANSCRIPTION_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            try:
                process.kill()
                await process.wait()
            except Exception:
                pass
            raise TimeoutError(
                f"Quá trình chuyển đổi vượt quá thời gian cho phép ({TRANSCRIPTION_TIMEOUT_SECONDS}s)."
            )

        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")
        return process.returncode, stdout_text, stderr_text

    @classmethod
    async def transcribe(
        cls,
        audio_path: str,
        title: str,
        target_dir: str,
        audio_duration_sec: Optional[float] = None
    ) -> TranscriptionResult:
        """
        Thực hiện chuyển đổi file âm thanh sang MIDI bằng mô hình Transkun.

        Args:
            audio_path (str): Đường dẫn file âm thanh đầu vào.
            title (str): Tiêu đề tác phẩm / tên file.
            target_dir (str): Thư mục lưu file kết quả.
            audio_duration_sec (Optional[float]): Thời lượng bài hát (nếu có).

        Returns:
            TranscriptionResult: Kết quả chi tiết của quá trình tạo MIDI.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Không tìm thấy file âm thanh đầu vào: {audio_path}")

        safe_title = sanitize_filename(title)
        output_midi_path = os.path.join(target_dir, f"{safe_title}.mid")

        device_flag, device_display_name, is_cuda = get_device_info()
        logger.info("Bắt đầu AI Transcription với thiết bị: %s (Flag: %s)", device_display_name, device_flag)

        start_time = time.time()
        try:
            returncode, stdout, stderr = await cls._execute_transcription(
                audio_path, output_midi_path, device_flag
            )

            # Nếu chạy trên CUDA bị lỗi (ví dụ: CUDA OOM hoặc CUDA driver error), tự động fallback về CPU
            if returncode != 0 and is_cuda:
                logger.warning(
                    "Transkun CUDA thất bại (code %d). Đang tự động thử lại với CPU...\nStderr: %s",
                    returncode,
                    stderr
                )
                device_flag = "cpu"
                device_display_name = "CPU (Auto Fallback)"
                is_cuda = False
                returncode, stdout, stderr = await cls._execute_transcription(
                    audio_path, output_midi_path, device_flag
                )

            elapsed_time = time.time() - start_time

            if returncode != 0:
                logger.error("Transkun gặp lỗi xử lý (code %d):\nStdout: %s\nStderr: %s", returncode, stdout, stderr)
                combined_err = f"{stderr}\n{stdout}".strip()

                if "No module named transkun" in combined_err or "command not found" in combined_err:
                    raise RuntimeError(
                        "Thư viện `transkun` chưa được cài đặt trong môi trường Python của Bot.\n"
                        "Vui lòng chạy `pip install transkun`."
                    )
                if "CUDA out of memory" in combined_err:
                    raise RuntimeError("Bộ nhớ VRAM của GPU không đủ để xử lý tác phẩm này.")

                raise RuntimeError(f"Lỗi phân tích âm thanh từ Transkun AI: {combined_err[-400:]}")

            if not os.path.exists(output_midi_path) or os.path.getsize(output_midi_path) == 0:
                raise RuntimeError("Mô hình Transkun hoàn thành nhưng không tạo được file MIDI đầu ra hợp lệ.")

            midi_size = os.path.getsize(output_midi_path)
            logger.info(
                "Chuyển đổi MIDI thành công! File: %s (Kích thước: %d bytes, Thời gian: %.2fs, Thiết bị: %s)",
                output_midi_path,
                midi_size,
                elapsed_time,
                device_display_name
            )

            return TranscriptionResult(
                midi_path=output_midi_path,
                midi_size_bytes=midi_size,
                audio_duration_sec=audio_duration_sec,
                elapsed_time_sec=elapsed_time,
                device_display_name=device_display_name,
                is_cuda=is_cuda
            )

        finally:
            # Giải phóng RAM và VRAM bộ nhớ đệm sau mỗi phiên xử lý
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
