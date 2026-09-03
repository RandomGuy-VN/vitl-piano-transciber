/**
 * Lệnh Slash /transcript: Chuyển đổi âm thanh (URL hoặc File tải lên) sang file MIDI qua Transkun AI.
 */

import { SlashCommandBuilder, AttachmentBuilder } from "discord.js";
import { DiscordEmbedBuilder } from "../services/embedBuilder.js";
import { AiClient } from "../services/aiClient.js";
import { logger } from "../utils/logger.js";
import { isSpotifyUrl, isYoutubeUrl } from "../utils/helpers.js";

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
    else if (url.includes("soundcloud.com")) sourceType = "SoundCloud";
    else sourceType = "Đường dẫn trực tiếp";
  }

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

      // Cập nhật Embed sang đang xử lý AI
      const processingEmbed = DiscordEmbedBuilder.createProcessingEmbed(
        attachment.name,
        null,
        "Transkun Neural Network",
        true
      );
      await interaction.editReply({ embeds: [processingEmbed] });

      // Gửi sang Python AI Core
      result = await AiClient.transcribeFromFile(buffer, attachment.name);
    } else {
      // Cập nhật Embed sang đang xử lý AI
      const processingEmbed = DiscordEmbedBuilder.createProcessingEmbed(
        sourceLabel,
        null,
        "Transkun Neural Network",
        true
      );
      await interaction.editReply({ embeds: [processingEmbed] });

      // Gửi URL sang Python AI Core
      result = await AiClient.transcribeFromUrl(url);
    }

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
    logger.error("Lỗi thực thi lệnh /transcript:", err);
    const errEmbed = DiscordEmbedBuilder.createErrorEmbed(
      "Xử lý chuyển đổi thất bại",
      err.message || String(err),
      "Vui lòng đảm bảo tệp/đường dẫn chứa âm thanh piano rõ ràng và không quá 15 phút."
    );
    await interaction.editReply({ embeds: [errEmbed] });
  }
}
