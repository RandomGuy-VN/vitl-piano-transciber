"""
Máy chủ Microservice Python cho Lõi AI Transkun (AI Core Server).
Chịu trách nhiệm tải âm thanh đa nguồn (pytubefix, Spotify oEmbed, direct audio),
quản lý hàng đợi Semaphore và thực hiện chuyển đổi Piano sang MIDI bằng mô hình Transkun AI.
Giao tiếp với Node.js Discord Bot qua REST API bất đồng bộ (aiohttp.web).
"""

import asyncio
import base64
import json
import logging
import os
import shutil
import sys
import tempfile
import time
from aiohttp import web
try:
    import psutil
except ImportError:
    psutil = None

# Thêm thư mục gốc của dự án vào sys.path để tận dụng các module đã viết
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import (
    MAX_FILE_SIZE_MB,
    MAX_AUDIO_DURATION_SECONDS,
    MAX_CONCURRENT_JOBS,
    PRELOAD_MODEL_ON_STARTUP,
    get_device_info,
    check_system_dependencies,
)
from services.transkun_service import TranskunService
from services.queue_manager import QueueManager
from services.audio_fetcher import AudioFetcher
from services.youtube_service import YouTubeService
from services.model_manager import ModelManager
from utils.logger import setup_logger
from utils.helpers import sanitize_filename, get_audio_duration_ffprobe, is_youtube_url, detect_source_name

logger = setup_logger("ai_core_server", level=logging.INFO)

AI_PORT = int(os.getenv("AI_CORE_PORT") or 5000)
AI_HOST = (os.getenv("AI_CORE_HOST") or "127.0.0.1").strip()

queue_manager = QueueManager()


async def handle_health(request: web.Request) -> web.Response:
    """Endpoint GET /health: Báo cáo trạng thái Lõi AI, phần cứng GPU/CPU và bộ nhớ RAM."""
    device_flag, device_display, is_cuda = get_device_info()
    mem_mb = 0.0
    if psutil:
        try:
            process = psutil.Process()
            mem_mb = process.memory_info().rss / (1024 * 1024)
        except Exception:
            pass

    data = {
        "status": "online",
        "service": "Vitl Piano Transkun AI Core",
        "device": device_display,
        "device_flag": device_flag,
        "is_cuda": is_cuda,
        "active_jobs": queue_manager.active_jobs,
        "max_concurrent_jobs": MAX_CONCURRENT_JOBS,
        "model_loaded": TranskunService.is_model_loaded(),
        "memory_usage_mb": round(mem_mb, 2),
        "dependencies": check_system_dependencies(),
    }
    return web.json_response(data)


async def handle_estimate(request: web.Request) -> web.Response:
    """
    Endpoint GET /estimate?url=...:
    Lấy nhanh metadata (thời lượng, tiêu đề) của URL mà KHÔNG tải âm thanh,
    để Node.js bot tính ETA (thời gian dự kiến xử lý) hiển thị cho người dùng.
    Hiện chỉ hỗ trợ ước lượng chính xác với YouTube; nguồn khác trả về duration None.
    """
    url = request.query.get("url", "").strip()
    if not url:
        return web.json_response(
            {"success": False, "error": "Thiếu tham số 'url' trên query string."},
            status=400
        )

    source_type = detect_source_name(url)
    duration = None
    title = None
    estimate_supported = False

    if is_youtube_url(url):
        # Bot-check của YouTube rất "flaky" (đôi khi pass, đôi khi không ngay cả
        # với cookies hợp lệ) -> thử tối đa 3 vòng, nghỉ 2s giữa các vòng.
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                # yt-dlp là thư viện đồng bộ -> chạy trong thread riêng để không block event loop.
                # download=False: chỉ lấy metadata (~1-5s), không tải âm thanh.
                def _meta():
                    return YouTubeService._extract_info_safe(url, download=False)

                info, _strategy_idx = await asyncio.wait_for(asyncio.to_thread(_meta), timeout=30.0)
                duration = info.get("duration")
                title = info.get("title")
                estimate_supported = duration is not None
                last_exc = None
                break
            except asyncio.TimeoutError:
                logger.warning("/estimate: lấy metadata YouTube quá chậm (>30s), vòng %d: %s", attempt + 1, url)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                logger.warning("/estimate: vòng %d không lấy được metadata: %s", attempt + 1, exc)
            if attempt < 2:
                await asyncio.sleep(2)
        if last_exc is not None and duration is None:
            logger.warning("/estimate: bỏ qua ước lượng cho %s", url)

    return web.json_response({
        "success": True,
        "url": url,
        "title": title,
        "source_type": source_type,
        "duration_sec": duration,
        "estimate_supported": estimate_supported,
        "active_jobs": queue_manager.active_jobs,
        "max_concurrent_jobs": MAX_CONCURRENT_JOBS,
        "model_loaded": TranskunService.is_model_loaded(),
    })


async def handle_transcribe(request: web.Request) -> web.Response:
    """
    Endpoint POST /transcribe:
    Nhận yêu cầu chuyển đổi âm thanh sang MIDI.
    Chấp nhận:
      - Multipart Form: 'file' (tệp âm thanh tải lên) và 'title' (tùy chọn)
      - JSON hoặc Form: 'url' (đường dẫn YouTube, Spotify, SoundCloud hoặc liên kết trực tiếp)
    """
    start_time = time.time()
    temp_dir = tempfile.mkdtemp(prefix="transkun_api_")

    try:
        url: str | None = None
        input_audio_path: str | None = None
        title: str = "Piano Transcription"
        audio_duration: float | None = None
        source_type: str = "Tệp tải lên"

        # 1. Bóc tách dữ liệu từ request
        if request.content_type == "application/json":
            json_data = await request.json()
            url = json_data.get("url")
            if json_data.get("title"):
                title = json_data.get("title")

        elif request.content_type.startswith("multipart/"):
            reader = await request.multipart()
            while True:
                field = await reader.next()
                if field is None:
                    break

                if field.name == "url":
                    url_bytes = await field.read()
                    url = url_bytes.decode("utf-8").strip()

                elif field.name == "title":
                    title_bytes = await field.read()
                    title = title_bytes.decode("utf-8").strip()

                elif field.name == "file":
                    filename = field.filename or "uploaded_audio.mp3"
                    title = os.path.splitext(filename)[0]
                    safe_name = sanitize_filename(title)
                    ext = os.path.splitext(filename)[1].lower() or ".mp3"
                    input_audio_path = os.path.join(temp_dir, f"{safe_name}{ext}")

                    size = 0
                    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
                    with open(input_audio_path, "wb") as f:
                        while True:
                            chunk = await field.read_chunk(64 * 1024)
                            if not chunk:
                                break
                            size += len(chunk)
                            if size > max_bytes:
                                return web.json_response(
                                    {"success": False, "error": f"Kích thước tệp vượt quá {MAX_FILE_SIZE_MB}MB."},
                                    status=400
                                )
                            f.write(chunk)

        else:
            post_data = await request.post()
            url = post_data.get("url")
            if post_data.get("title"):
                title = post_data.get("title")

        # 2. Xử lý tải âm thanh nếu truyền URL
        if url:
            logger.info("Yêu cầu xử lý từ URL: %s", url)
            audio_info = await AudioFetcher.fetch_url(url, temp_dir)
            input_audio_path = audio_info.file_path
            title = audio_info.title
            audio_duration = audio_info.duration_sec
            source_type = audio_info.source_type
        elif not input_audio_path or not os.path.exists(input_audio_path):
            return web.json_response(
                {"success": False, "error": "Vui lòng cung cấp tham số 'url' hoặc tệp tải lên 'file'."},
                status=400
            )
        else:
            audio_duration = get_audio_duration_ffprobe(input_audio_path)

        # 3. Kiểm tra thời lượng âm thanh
        if audio_duration and audio_duration > MAX_AUDIO_DURATION_SECONDS:
            max_mins = MAX_AUDIO_DURATION_SECONDS // 60
            return web.json_response(
                {"success": False, "error": f"Thời lượng âm thanh ({int(audio_duration)}s) vượt quá giới hạn ({max_mins} phút)."},
                status=400
            )

        # 4. Đưa vào hàng đợi xử lý AI thông minh qua QueueManager
        async with queue_manager.acquire_slot() as queue_pos:
            logger.info("Đang bắt đầu AI inference cho: %s (Queue pos: %d)", title, queue_pos)
            transcription_res = await TranskunService.transcribe(
                audio_path=input_audio_path,
                title=title,
                target_dir=temp_dir,
                audio_duration_sec=audio_duration
            )

        # 5. Đọc file MIDI kết quả và mã hóa Base64 để gửi trả về cho Node.js
        with open(transcription_res.midi_path, "rb") as mf:
            midi_bytes = mf.read()
        midi_base64 = base64.b64encode(midi_bytes).decode("utf-8")

        response_data = {
            "success": True,
            "title": title,
            "source_type": source_type,
            "audio_duration_sec": transcription_res.audio_duration_sec,
            "midi_size_bytes": transcription_res.midi_size_bytes,
            "elapsed_time_sec": round(transcription_res.elapsed_time_sec, 2),
            "device_display": transcription_res.device_display_name,
            "filename": os.path.basename(transcription_res.midi_path),
            "midi_base64": midi_base64
        }

        logger.info("Chuyển đổi hoàn tất thành công cho: %s trong %.2fs", title, time.time() - start_time)
        return web.json_response(response_data)

    except Exception as exc:
        logger.exception("Lỗi trong quá trình xử lý AI transcription: %s", exc)
        return web.json_response({"success": False, "error": str(exc)}, status=500)

    finally:
        # Dọn dẹp thư mục tạm an toàn
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


async def init_app() -> web.Application:
    """Khởi tạo ứng dụng web aiohttp."""
    app = web.Application(client_max_size=100 * 1024 * 1024)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/status", handle_health)
    app.router.add_get("/estimate", handle_estimate)
    app.router.add_post("/transcribe", handle_transcribe)
    return app


async def main() -> None:
    """Điểm khởi động máy chủ AI Core."""
    logger.info("=" * 60)
    logger.info("   🎹 KHỞI ĐỘNG VITL PIANO AI CORE SERVICE (PYTHON) 🎹")
    logger.info("=" * 60)

    device_flag, device_display, is_cuda = get_device_info()
    logger.info("Thiết bị AI       : %s [Flag: %s, CUDA: %s]", device_display, device_flag, is_cuda)
    logger.info("Cổng AI Core HTTP : %s:%d", AI_HOST, AI_PORT)

    # Tự động nạp trước model nếu được bật
    if PRELOAD_MODEL_ON_STARTUP:
        # Nạp model Transkun in-process NGAY LÚC KHỞI ĐỘNG (dùng chung mọi job,
        # không cần nạp lại mỗi request). Fallback về warmup CLI cũ nếu lỗi.
        async def _warm_inprocess_model():
            try:
                device_flag, _disp, _cuda = get_device_info()
                await asyncio.to_thread(TranskunService._load_model, device_flag)
                logger.info("Warmup in-process model hoàn tất.")
            except Exception as warm_err:  # noqa: BLE001
                logger.warning("Warmup in-process model lỗi (%s) — sẽ fallback CLI khi chạy.", warm_err)

        asyncio.create_task(_warm_inprocess_model())

    app = await init_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, AI_HOST, AI_PORT)
    await site.start()

    logger.info("-> AI Core Service đã sẵn sàng lắng nghe tại http://%s:%d", AI_HOST, AI_PORT)
    logger.info("=" * 60)

    # Giữ tiến trình chạy liên tục
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Dừng AI Core Service.")
