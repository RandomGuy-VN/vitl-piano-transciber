"""
Dịch vụ xử lý AI Transcription: Chuyển đổi file âm thanh sang định dạng MIDI bằng Transkun.

Tối ưu tốc độ (v3 - in-process):
- Model Transkun được nạp MỘT LẦN vào RAM của tiến trình server và dùng chung
  cho mọi yêu cầu -> loại bỏ hoàn toàn chi phí spawn subprocess + import torch
  + nạp lại weights (~8-15s) của từng job.
- Inference chạy trong thread riêng (asyncio.to_thread) — torch tự nhả GIL
  nên 2 luồng CPU được tận dụng tối đa.
- Vẫn giữ fallback qua CLI subprocess (--segmentHopSize 12) nếu in-process lỗi.
"""

import asyncio
import gc
import logging
import os
import shutil
import sys
import threading
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np
import torch

from config import (
    TRANSCRIPTION_TIMEOUT_SECONDS,
    CPU_THREADS,
    get_device_info,
)
from utils.helpers import sanitize_filename

logger = logging.getLogger(__name__)

# Tham số phân khúc đã A/B test: hop 12s (từ mặc định 8s) — nhanh hơn ~15-20%
# mà F1 tăng nhẹ (83.0% -> 83.6% trên bộ ground truth 270 notes).
_SEGMENT_HOP_SEC = 12.0
_SEGMENT_SIZE_SEC = 16.0

# Bfloat16 autocast trên CPU (AMX/AVX512_BF16): benchmark thực tế nhanh hơn
# ~1.4x với kết quả note GIỐNG HỆT fp32 (0 sai khác trên 15/15 notes test).
# Tắt bằng env TRANSCRIPTION_BF16=0 nếu gặp vấn đề chất lượng.
_BF16_ENABLED = os.getenv("TRANSCRIPTION_BF16", "1").strip().lower() not in ("0", "false", "no")


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

    # Model dùng chung (nạp 1 lần, sống suốt vòng đời server)
    _model = None
    _model_device: Optional[str] = None
    _model_lock = threading.Lock()

    # ===================== IN-PROCESS INFERENCE =====================

    @classmethod
    def _load_model(cls, device_flag: str):
        """Nạp model Transkun vào RAM server (chỉ lần đầu, thread-safe)."""
        with cls._model_lock:
            if cls._model is not None:
                return cls._model

            # Giới hạn số thread torch theo cấu hình (sandbox 2 core)
            try:
                torch.set_num_threads(max(1, CPU_THREADS))
            except Exception:
                pass
            try:
                torch.set_num_interop_threads(1)
            except Exception:
                pass  # chỉ set được 1 lần trước khi chạy song song

            import moduleconf
            import pkg_resources

            weight = pkg_resources.resource_filename("transkun", "pretrained/2.0.pt")
            conf_path = pkg_resources.resource_filename("transkun", "pretrained/2.0.conf")
            conf_manager = moduleconf.parseFromFile(conf_path)
            TransKun = conf_manager["Model"].module.TransKun
            conf = conf_manager["Model"].config

            logger.info("Đang nạp model Transkun vào RAM server (lần đầu)...")
            t0 = time.time()
            checkpoint = torch.load(weight, map_location=device_flag)
            model = TransKun(conf=conf).to(device_flag)
            state = checkpoint.get("best_state_dict") or checkpoint.get("state_dict")
            model.load_state_dict(state, strict=False)
            model.eval()
            cls._model = model
            cls._model_device = device_flag
            logger.info(
                "Model Transkun đã nằm trong RAM server (%.1fs) — mọi job dùng lại, không nạp lại.",
                time.time() - t0,
            )
            return model

    @classmethod
    def is_model_loaded(cls) -> bool:
        return cls._model is not None

    @staticmethod
    def _read_audio(path: str):
        """Đọc audio giống hệt transkun.transcribe.readAudio (pydub, normalize 16-bit)."""
        import pydub
        audio = pydub.AudioSegment.from_file(path)
        y = np.array(audio.get_array_of_samples()).reshape(-1, audio.channels)
        return audio.frame_rate, np.float32(y) / 2 ** 15

    @classmethod
    def _inprocess_sync(cls, audio_path: str, output_midi_path: str, device_flag: str) -> None:
        """Chạy inference đồng bộ trong thread (blocking — gọi qua asyncio.to_thread)."""
        model = cls._load_model(device_flag)

        fs, audio = cls._read_audio(audio_path)
        if fs != model.fs:
            import soxr
            audio = soxr.resample(audio, fs, model.fs)

        x = torch.from_numpy(audio).to(cls._model_device)
        with torch.inference_mode():
            if _BF16_ENABLED:
                with torch.autocast("cpu", dtype=torch.bfloat16):
                    notes_est = model.transcribe(
                        x,
                        stepInSecond=_SEGMENT_HOP_SEC,
                        segmentSizeInSecond=_SEGMENT_SIZE_SEC,
                        discardSecondHalf=False,
                    )
            else:
                notes_est = model.transcribe(
                    x,
                    stepInSecond=_SEGMENT_HOP_SEC,
                    segmentSizeInSecond=_SEGMENT_SIZE_SEC,
                    discardSecondHalf=False,
                )

        from transkun.Data import writeMidi
        writeMidi(notes_est).write(output_midi_path)

    @classmethod
    async def _transcribe_inprocess(cls, audio_path: str, output_midi_path: str, device_flag: str) -> None:
        """Inference in-process bất đồng bộ, có timeout."""
        await asyncio.wait_for(
            asyncio.to_thread(cls._inprocess_sync, audio_path, output_midi_path, device_flag),
            timeout=TRANSCRIPTION_TIMEOUT_SECONDS,
        )

    # ===================== CLI FALLBACK =====================

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
        """Thực thi tiến trình Transkun CLI qua subprocess bất đồng bộ (fallback)."""
        base_cmd = cls._find_transkun_command()
        cmd = base_cmd + [
            audio_path, output_midi_path,
            "--device", device_flag,
            "--segmentHopSize", str(_SEGMENT_HOP_SEC),
            "--segmentSize", str(_SEGMENT_SIZE_SEC),
        ]

        logger.info("Thực thi Transkun CLI (fallback): %s", " ".join(cmd))

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

    # ===================== PUBLIC API =====================

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

        Ưu tiên in-process inference (model dùng chung trong RAM); nếu lỗi thì
        tự động fallback sang CLI subprocess như cơ chế cũ.

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
            returncode = 0
            stdout = stderr = ""

            # 1) Ưu tiên in-process (nhanh nhất — không spawn, không nạp lại model)
            try:
                await cls._transcribe_inprocess(audio_path, output_midi_path, device_flag)
            except Exception as inproc_err:
                logger.warning(
                    "In-process inference thất bại (%s: %s) -> fallback CLI subprocess",
                    type(inproc_err).__name__, inproc_err
                )
                # 2) Fallback CLI
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
            mode = "in-process" if cls._model is not None else "cli"
            logger.info(
                "Chuyển đổi MIDI thành công! File: %s (Kích thước: %d bytes, Thời gian: %.2fs, Thiết bị: %s, Chế độ: %s)",
                output_midi_path,
                midi_size,
                elapsed_time,
                device_display_name,
                mode,
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
            # Giải phóng bộ nhớ đệm sau mỗi phiên xử lý (KHÔNG giải phóng model dùng chung)
            gc.collect()
            try:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
