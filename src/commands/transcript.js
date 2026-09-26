/**
 * Lệnh Slash /transcript: Chuyển đổi âm thanh (URL hoặc File tải lên) sang file MIDI qua Transkun AI.
 * Có hiển thị ETA (thời gian dự kiến) và tiến trình chạy thực tế cập nhật định kỳ.
 */

import { SlashCommandBuilder, AttachmentBuilder } from "discord.js";
import { DiscordEmbedBuilder } from "../services/embedBuilder.js";
import { AiClient } from "../services/aiClient.js";
import { logger } from "../utils/logger.js";
import { isSpotifyUrl, isYoutubeUrl, isSoundcloudUrl, formatElapsedTime, formatEta, buildEtaInfo } from "../utils/helpers.js";

/** Khoảng cách cập nhật tiến trình live lên Discord (10s — an toàn về rate-limit). */
const PROGRESS_INTERVAL_MS = 10_000;

export const data = new SlashCommandBuilder()
  .setName("transcript")
  .setDescription("Chuyển đổi âm thanh piano (URL hoặc file đính kèm) sang file MIDI (.mid)")
  .addStringOption((option) =>
    option
      .setName("url")
      .setDescription("Đường dẫn âm thanh từ YouTube, Spotify, SoundCloud hoặc link trực tiếp")
      .setRequired(false)
  )
  .addAttachmentOption((option) =>
    option
      .setName("file")
      .setDescription("Tệp âm thanh tải lên trực tiếp (.mp3, .wav, .flac, .m4a, v.v.)")
      .setRequired(false)
  );

export async function execute(interaction) {
  const url = interaction.options.getString("url");
  const attachment = interaction.options.getAttachment("file");

  // 1. Kiểm tra tham số đầu vào
  if (!url && !attachment) {
    const errorEmbed = DiscordEmbedBuilder.createErrorEmbed(
      "Thiếu tham số đầu vào",
      "Bạn phải cung cấp ít nhất một tham số:\n- `url`: Đường dẫn từ YouTube, Spotify, SoundCloud...\n- `file`: Tệp âm thanh đính kèm trực tiếp.",
      "Ví dụ: /transcript url:https://youtu.be/example hoặc tải lên một file .mp3"
    );
    return await interaction.reply({ embeds: [errorEmbed], ephemeral: true });
  }

  // 2. Defer phản hồi để không bị timeout 3s của Discord
  await interaction.deferReply();

  const sourceLabel = url || attachment.name;
  let sourceType = "Tệp tải lên";
  if (url) {
    if (isYoutubeUrl(url)) sourceType = "YouTube";
    else if (isSpotifyUrl(url)) sourceType = "Spotify";
    else if (isSoundcloudUrl(url)) sourceType = "SoundCloud";
    else sourceType = "Đường dẫn trực tiếp";
  }

  // === Bộ máy tiến trình live: timer đếm thời gian đã chạy + cập nhật embed định kỳ ===
  const startedAt = Date.now();
  let progressTimer = null;

  const stopProgress = () => {
    if (progressTimer) {
      clearInterval(progressTimer);
      progressTimer = null;
    }
  };

  const startProgress = (buildEmbed) => {
    stopProgress();
    progressTimer = setInterval(async () => {
      try {
        const elapsedSec = (Date.now() - startedAt) / 1000;
        await interaction.editReply({ embeds: [buildEmbed(elapsedSec)] });
      } catch {
        // Người dùng xóa tin nhắn / interaction hết hạn -> ngừng cập nhật
        stopProgress();
      }
    }, PROGRESS_INTERVAL_MS);
    // Không giữ event loop nếu mọi thứ khác đã xong
    if (progressTimer.unref) progressTimer.unref();
  };

  const elapsedNow = () => formatElapsedTime((Date.now() - startedAt) / 1000);

  // 3. Hiển thị Embed Đang tải / Hàng đợi
  const downloadingEmbed = DiscordEmbedBuilder.createDownloadingEmbed(sourceLabel, sourceType);
  await interaction.editReply({ embeds: [downloadingEmbed] });

  try {
    let result;

    if (attachment) {
      // Tải buffer của attachment
      const fileResp = await fetch(attachment.url);
      if (!fileResp.ok) {
        throw new Error(`Không thể tải tệp đính kèm từ Discord (HTTP ${fileResp.status}).`);
      }
      const arrayBuffer = await fileResp.arrayBuffer();
      const buffer = Buffer.from(arrayBuffer);

      // File tải lên: chưa biết trước thời lượng -> chỉ hiển thị tiến trình đã chạy
      const buildFileProgress = (elapsedSec) =>
        DiscordEmbedBuilder.createProcessingEmbed(
          attachment.name,
          null,
          "Transkun Neural Network",
          false,
          null,
          `${formatElapsedTime(elapsedSec)} đã chạy`
        );

      const processingEmbed = buildFileProgress(0);
      await interaction.editReply({ embeds: [processingEmbed] });
      startProgress(buildFileProgress);

      // Gửi sang Python AI Core
      result = await AiClient.transcribeFromFile(buffer, attachment.name);
    } else {
      // === URL flow: hỏi AI Core metadata nhanh để tính ETA chính xác theo thời lượng ===
      let etaInfo = null;
      let videoTitle = sourceLabel;

      if (isYoutubeUrl(url)) {
        const est = await AiClient.estimateUrl(url);
        if (est) {
          etaInfo = buildEtaInfo({
            durationSec: est.duration_sec,
            activeJobs: est.active_jobs,
            maxConcurrentJobs: est.max_concurrent_jobs,
          });
          if (est.title) videoTitle = est.title;
        }
      }

      // Cập nhật Embed đang tải kèm ETA (nếu ước lượng được)
      const downloadingWithEta = DiscordEmbedBuilder.createDownloadingEmbed(
        sourceLabel,
        sourceType,
        etaInfo ? `Tổng: ${etaInfo.totalText} (${etaInfo.detailText})` : null
      );
      await interaction.editReply({ embeds: [downloadingWithEta] });

      // Chuyển sang Embed xử lý AI với ETA + tiến trình live (đếm ngược theo ETA)
      const etaSec = etaInfo ? etaInfo.totalSec : null;
      const buildUrlProgress = (elapsedSec) => {
        let progressText = `${formatElapsedTime(elapsedSec)} đã chạy`;
        if (etaSec) {
          const remaining = Math.max(0, etaSec - elapsedSec);
          progressText += ` • ${remaining > 5 ? `còn ${formatEta(remaining)}` : "sắp xong..."}`;
        }
        return DiscordEmbedBuilder.createProcessingEmbed(
          videoTitle,
          null,
          "Transkun Neural Network",
          false,
          etaInfo ? etaInfo.totalText : null,
          progressText
        );
      };

      const processingEmbed = buildUrlProgress(0);
      await interaction.editReply({ embeds: [processingEmbed] });
      startProgress(buildUrlProgress);

      // Gửi URL sang Python AI Core (bao gồm cả giai đoạn tải về phía AI Core)
      result = await AiClient.transcribeFromUrl(url);
    }

    stopProgress();

    // 4. Tạo file MIDI attachment từ buffer
    const midiAttachment = new AttachmentBuilder(result.midiBuffer, {
      name: result.filename,
      description: `MIDI trích xuất bởi Vitl Piano Bot - ${result.title}`,
    });

    // 5. Hiển thị Embed thành công và đính kèm file
    const successEmbed = DiscordEmbedBuilder.createSuccessEmbed(
      result.title,
      result.midiSizeBytes,
      result.audioDurationSec,
      result.elapsedTimeSec,
      result.deviceDisplay
    );

    await interaction.editReply({
      embeds: [successEmbed],
      files: [midiAttachment],
    });

    logger.info(`Đã hoàn thành lệnh /transcript cho: ${result.title}`);
  } catch (err) {
    stopProgress();
    logger.error("Lỗi thực thi lệnh /transcript:", err);
    const errEmbed = DiscordEmbedBuilder.createErrorEmbed(
      "Xử lý chuyển đổi thất bại",
      err.message || String(err),
      "Vui lòng đảm bảo tệp/đường dẫn chứa âm thanh piano rõ ràng và không quá 15 phút."
    );
    await interaction.editReply({ embeds: [errEmbed] });
  } finally {
    stopProgress();
  }
}
