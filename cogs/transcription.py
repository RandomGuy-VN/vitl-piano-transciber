"""
Cog xử lý Slash Command /transcript cho Vitl Piano Bot.
Tích hợp hàng đợi thông minh (QueueManager), tối ưu hóa tài nguyên Cloud và dọn dẹp bộ nhớ tạm.
"""

import logging
import os
import shutil
import tempfile
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from config import get_device_info
from services.audio_fetcher import AudioFetcher, AudioSourceInfo
from services.embed_builder import EmbedBuilder
from services.queue_manager import job_queue
from services.transkun_service import TranskunService
from utils.helpers import sanitize_filename, detect_source_name

logger = logging.getLogger(__name__)


class TranscriptionCog(commands.Cog):
    """Cog phụ trách tác vụ chuyển đổi âm thanh sang MIDI."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="transcript",
        description="Chuyển đổi âm thanh (YouTube, Spotify, SoundCloud, MP3/WAV) sang file MIDI bằng Transkun AI"
    )
    @app_commands.describe(
        url="Đường dẫn âm thanh từ YouTube, Spotify, SoundCloud hoặc file trực tiếp",
        file="Tệp âm thanh đính kèm tải lên từ thiết bị của bạn (MP3, WAV, FLAC, M4A, v.v.)"
    )
    async def transcript(
        self,
        interaction: discord.Interaction,
        url: Optional[str] = None,
        file: Optional[discord.Attachment] = None
    ) -> None:
        """
        Lệnh Slash chính thực hiện quy trình trích xuất và chuyển đổi âm thanh sang MIDI.
        """
        # ==========================================
        # BƯỚC 1: XÁC THỰC THAM SỐ ĐẦU VÀO
        # ==========================================
        if not url and not file:
            err_embed = EmbedBuilder.create_error_embed(
                error_title="Thiếu thông tin đầu vào",
                error_description="Bạn cần cung cấp ít nhất một trong hai tham số:\n• `url`: Đường dẫn từ YouTube, Spotify, SoundCloud...\n• `file`: Tệp âm thanh đính kèm (MP3, WAV, v.v.)",
                suggestion="Ví dụ:\n`/transcript url:https://youtu.be/...`\nhoặc `/transcript file:piano_song.mp3`"
            )
            await interaction.response.send_message(embed=err_embed, ephemeral=True)
            return

        # ==========================================
        # BƯỚC 2: TRÌ HOÃN PHẢN HỒI (DEFER)
        # ==========================================
        await interaction.response.defer(thinking=True)

        if file is not None:
            source_label = file.filename
            source_type = "Tệp đính kèm"
        else:
            source_label = url or "URL"
            source_type = detect_source_name(url or "")

        # ==========================================
        # BƯỚC 3: QUẢN LÝ HÀNG ĐỢI (QUEUE CONCURRENCY)
        # ==========================================
        # Nếu hệ thống đang bận, thông báo vị trí hàng chờ cho người dùng
        if job_queue.waiting_jobs > 0 or job_queue.active_jobs >= 1:
            queued_embed = EmbedBuilder.create_queued_embed(
                source_label=source_label,
                source_type=source_type,
                queue_position=job_queue.waiting_jobs + 1,
                active_jobs=job_queue.active_jobs
            )
            await interaction.edit_original_response(embed=queued_embed)

        async with job_queue.acquire_slot() as initial_queue_pos:
            # ==========================================
            # BƯỚC 4: KHỞI TẠO THƯ MỤC TẠM (TEMP DIR)
            # ==========================================
            temp_dir_obj = tempfile.TemporaryDirectory(prefix="vitl_piano_")
            temp_dir = temp_dir_obj.name

            try:
                # ----------------------------------------------------
                # BƯỚC 5: THU THẬP & TẢI ÂM THANH (AUDIO FETCHING)
                # ----------------------------------------------------
                downloading_embed = EmbedBuilder.create_downloading_embed(
                    source_label=source_label,
                    source_type=source_type
                )
                await interaction.edit_original_response(embed=downloading_embed)

                # Thực hiện tải file âm thanh
                if file is not None:
                    audio_info: AudioSourceInfo = await AudioFetcher.fetch_attachment(
                        attachment=file,
                        target_dir=temp_dir
                    )
                else:
                    audio_info: AudioSourceInfo = await AudioFetcher.fetch_url(
                        url=url,
                        target_dir=temp_dir
                    )

                # ----------------------------------------------------
                # BƯỚC 6: CHUYỂN ĐỔI MIDI BẰNG TRANSKUN (TRANSCRIPTION)
                # ----------------------------------------------------
                _, device_display, is_cuda = get_device_info()
                processing_embed = EmbedBuilder.create_processing_embed(
                    title=audio_info.title,
                    duration_sec=audio_info.duration_sec,
                    device_display_name=device_display,
                    is_cuda=is_cuda
                )
                await interaction.edit_original_response(embed=processing_embed)

                transcription_result = await TranskunService.transcribe(
                    audio_path=audio_info.file_path,
                    title=audio_info.title,
                    target_dir=temp_dir,
                    audio_duration_sec=audio_info.duration_sec
                )

                # ----------------------------------------------------
                # BƯỚC 7: GỬI KẾT QUẢ CHO NGƯỜI DÙNG
                # ----------------------------------------------------
                safe_filename = sanitize_filename(audio_info.title)
                discord_file = discord.File(
                    fp=transcription_result.midi_path,
                    filename=f"{safe_filename}.mid",
                    description=f"MIDI Transcription for {audio_info.title}"
                )

                success_embed = EmbedBuilder.create_success_embed(
                    title=audio_info.title,
                    midi_size_bytes=transcription_result.midi_size_bytes,
                    audio_duration_sec=audio_info.duration_sec,
                    elapsed_time_sec=transcription_result.elapsed_time_sec,
                    device_display_name=transcription_result.device_display_name
                )

                await interaction.edit_original_response(
                    embed=success_embed,
                    attachments=[discord_file]
                )
                logger.info("Hoàn tất pipeline /transcript thành công cho người dùng: %s", interaction.user)

            except ValueError as val_err:
                logger.warning("Lỗi xác thực dữ liệu đầu vào: %s", val_err)
                err_embed = EmbedBuilder.create_error_embed(
                    error_title="Thông tin đầu vào không hợp lệ",
                    error_description=str(val_err),
                    suggestion="Vui lòng kiểm tra lại liên kết hoặc định dạng tệp và thử lại."
                )
                await interaction.edit_original_response(embed=err_embed, attachments=[])

            except TimeoutError as to_err:
                logger.error("Hết thời gian xử lý: %s", to_err)
                err_embed = EmbedBuilder.create_error_embed(
                    error_title="Quá thời gian xử lý (Timeout)",
                    error_description=str(to_err),
                    suggestion="Hệ thống có thể đang bận hoặc bản nhạc quá dài. Vui lòng thử lại với bản nhạc ngắn hơn."
                )
                await interaction.edit_original_response(embed=err_embed, attachments=[])

            except FileNotFoundError as fnf_err:
                logger.error("Không tìm thấy tệp: %s", fnf_err)
                err_embed = EmbedBuilder.create_error_embed(
                    error_title="Không tìm thấy tệp âm thanh",
                    error_description=str(fnf_err),
                    suggestion="Quá trình tải file đã gặp sự cố. Vui lòng thử lại với một nguồn khác."
                )
                await interaction.edit_original_response(embed=err_embed, attachments=[])

            except Exception as exc:
                logger.exception("Lỗi không xác định trong quá trình xử lý /transcript: %s", exc)
                err_embed = EmbedBuilder.create_error_embed(
                    error_title="Đã xảy ra sự cố trong quá trình chuyển đổi",
                    error_description=str(exc),
                    suggestion="Nếu sự cố tiếp tục tái diễn, vui lòng liên hệ quản trị viên hoặc kiểm tra trạng thái GPU/CPU."
                )
                await interaction.edit_original_response(embed=err_embed, attachments=[])

            finally:
                # ==========================================
                # BƯỚC 8: DỌN DẸP THƯ MỤC TẠM (CLEANUP)
                # ==========================================
                try:
                    temp_dir_obj.cleanup()
                    logger.debug("Đã dọn dẹp thư mục tạm: %s", temp_dir)
                except Exception as clean_err:
                    logger.warning("Không thể xóa thư mục tạm %s: %s", temp_dir, clean_err)


async def setup(bot: commands.Bot) -> None:
    """Hàm đăng ký Cog vào Discord Bot."""
    await bot.add_cog(TranscriptionCog(bot))
