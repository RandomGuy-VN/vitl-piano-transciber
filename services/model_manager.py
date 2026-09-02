"""
Dịch vụ quản lý và tải trước (Pre-loading / Warmup) mô hình Transkun AI khi khởi động.
Giúp loại bỏ hoàn toàn độ trễ tải trọng số mô hình khi có người dùng đầu tiên gửi yêu cầu.
"""

import asyncio
import logging
import os
import sys
import tempfile
import time
import shutil

logger = logging.getLogger(__name__)


class ModelManager:
    """Quản lý nạp trước và kiểm tra tính toàn vẹn của mô hình AI."""

    @classmethod
    async def preload_and_warmup(cls) -> bool:
        """
        Thực hiện tạo một đoạn âm thanh ngắn mô phỏng và chạy Transkun một lần khi khởi động
        để tự động tải weights về bộ nhớ đệm (cache) và làm nóng mô hình.
        """
        logger.info("Đang kiểm tra và nạp trước trọng số mô hình Transkun AI (Warmup)...")
        start_time = time.time()

        with tempfile.TemporaryDirectory(prefix="vitl_warmup_") as tmpdir:
            # Tạo 1 file WAV mẫu siêu ngắn (0.5s) chứa sóng sin để Transkun khởi động
            dummy_wav = os.path.join(tmpdir, "warmup.wav")
            dummy_mid = os.path.join(tmpdir, "warmup.mid")

            try:
                import numpy as np
                import wave
                import struct

                # Tạo âm thanh sin 440Hz dài 0.5s ở tần số 44100Hz
                sample_rate = 44100
                duration = 0.5
                num_samples = int(sample_rate * duration)
                t = np.linspace(0, duration, num_samples, endpoint=False)
                audio_data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

                with wave.open(dummy_wav, "w") as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(audio_data.tobytes())

            except Exception as dummy_err:
                logger.debug("Không thể tạo file WAV mẫu bằng numpy/wave: %s", dummy_err)
                # Fallback dùng ffmpeg nếu có
                ffmpeg_bin = shutil.which("ffmpeg")
                if ffmpeg_bin:
                    try:
                        subprocess_cmd = [
                            ffmpeg_bin, "-y", "-f", "lavfi",
                            "-i", "sine=frequency=440:duration=0.5",
                            dummy_wav
                        ]
                        proc = await asyncio.create_subprocess_exec(
                            *subprocess_cmd,
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.DEVNULL
                        )
                        await proc.wait()
                    except Exception:
                        pass

            if not os.path.exists(dummy_wav):
                logger.warning("Bỏ qua bước warmup do không tạo được file âm thanh mẫu.")
                return False

            # Chạy thử lệnh Transkun
            transkun_bin = shutil.which("transkun")
            cmd = [transkun_bin] if transkun_bin else [sys.executable, "-m", "transkun.transcribe"]
            cmd += [dummy_wav, dummy_mid, "--device", "cpu"]

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

                if proc.returncode == 0:
                    elapsed = round(time.time() - start_time, 2)
                    logger.info("-> Nạp trước mô hình Transkun AI hoàn tất trong %.2fs. Hệ thống đã sẵn sàng!", elapsed)
                    return True
                else:
                    logger.warning("Warmup mô hình trả về mã lỗi %d: %s", proc.returncode, stderr.decode(errors="replace")[:200])
                    return False
            except Exception as warmup_err:
                logger.warning("Không thể nạp trước mô hình: %s", warmup_err)
                return False
