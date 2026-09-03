/**
 * Xây dựng các giao diện Discord Embed chuẩn cho toàn bộ quy trình xử lý.
 */

import { EmbedBuilder } from "discord.js";
import { formatBytes, formatDuration, formatElapsedTime } from "../utils/helpers.js";

export const COLORS = {
  QUEUED: 0xFFA500,       // Cam
  DOWNLOADING: 0x3498DB,  // Xanh dương
  PROCESSING: 0x9B59B6,   // Tím
  SUCCESS: 0x2ECC71,      // Xanh lá
  ERROR: 0xE74C3C,        // Đỏ
};

export class DiscordEmbedBuilder {
  /**
   * Embed 1: Đang chờ trong hàng đợi AI (Queue)
   */
  static createQueuedEmbed(sourceLabel, sourceType, queuePosition = 1, activeJobs = 1) {
    return new EmbedBuilder()
      .setTitle("⏳ Đang chờ trong hàng chờ AI...")
      .setDescription(
        "Hệ thống đang xử lý các yêu cầu trước để đảm bảo bộ nhớ và hiệu năng AI tốt nhất. " +
        "Yêu cầu của bạn sẽ được bắt đầu ngay khi có tài nguyên trống."
      )
      .setColor(COLORS.QUEUED)
      .addFields(
        { name: "🎵 Tác phẩm", value: `\`${sourceLabel}\``, inline: false },
        { name: "📍 Vị trí hàng chờ", value: `#${queuePosition}`, inline: true },
        { name: "⚡ Luồng đang chạy", value: `${activeJobs} tác vụ`, inline: true },
        { name: "📦 Nguồn âm thanh", value: sourceType, inline: true }
      )
      .setFooter({ text: "Vitl Piano Bot • AI Queue Manager" })
      .setTimestamp();
  }

  /**
   * Embed 2: Đang tải âm thanh
   */
  static createDownloadingEmbed(sourceLabel, sourceType) {
    return new EmbedBuilder()
      .setTitle("📥 Đang tải và trích xuất âm thanh...")
      .setDescription(
        `Đang kết nối tới **${sourceType}** để lấy luồng âm thanh gốc độ phân giải cao.`
      )
      .setColor(COLORS.DOWNLOADING)
      .addFields(
        { name: "🔗 Nguồn", value: `\`${sourceLabel}\``, inline: false },
        { name: "📡 Trạng thái", value: "Đang tải luồng âm thanh và chuẩn hóa dữ liệu...", inline: false }
      )
      .setFooter({ text: "Vitl Piano Bot • Audio Ingestion Pipeline" })
      .setTimestamp();
  }

  /**
   * Embed 3: Đang phân tích AI (Transkun)
   */
  static createProcessingEmbed(title, durationSec, deviceDisplayName = "GPU Acceleration", isCuda = false) {
    const durStr = formatDuration(durationSec);
    const hwIcon = isCuda ? "🚀 GPU" : "⚙️ CPU";

    return new EmbedBuilder()
      .setTitle("🧠 Đang phân tích nốt nhạc bằng Transkun AI...")
      .setDescription(
        "Mô hình Deep Learning đang nghe và nhận diện cao độ (pitch), vận tốc phím (velocity), " +
        "và bàn đạp vang (pedal) của từng nốt piano."
      )
      .setColor(COLORS.PROCESSING)
      .addFields(
        { name: "🎹 Tiêu đề", value: `**${title}**`, inline: false },
        { name: "⏱️ Thời lượng", value: durStr, inline: true },
        { name: "🖥️ Phần cứng AI", value: `${hwIcon} (${deviceDisplayName})`, inline: true }
      )
      .setFooter({ text: "Vitl Piano Bot • Transkun Neural Network Inference" })
      .setTimestamp();
  }

  /**
   * Embed 4: Hoàn thành thành công
   */
  static createSuccessEmbed(title, midiSizeBytes, audioDurationSec, elapsedTimeSec, deviceDisplayName = "AI Core") {
    const durStr = formatDuration(audioDurationSec);
    const sizeStr = formatBytes(midiSizeBytes);
    const timeStr = formatElapsedTime(elapsedTimeSec);

    return new EmbedBuilder()
      .setTitle("🎹 Chuyển đổi thành công sang MIDI!")
      .setDescription(
        "File MIDI chuẩn (.mid) đã được trích xuất hoàn tất. " +
        "Bạn có thể tải về để mở trong **Synthesia**, **MuseScore**, **FL Studio**, **Logic Pro**, v.v."
      )
      .setColor(COLORS.SUCCESS)
      .addFields(
        { name: "🎼 Tên tác phẩm", value: `**${title}**`, inline: false },
        { name: "💾 Dung lượng MIDI", value: sizeStr, inline: true },
        { name: "🎵 Thời lượng gốc", value: durStr, inline: true },
        { name: "⚡ Thời gian xử lý", value: timeStr, inline: true },
        { name: "🖥️ Thiết bị AI", value: deviceDisplayName, inline: true }
      )
      .setFooter({ text: "Vitl Piano Bot • AI Transcription Completed" })
      .setTimestamp();
  }

  /**
   * Embed 5: Lỗi
   */
  static createErrorEmbed(errorTitle, errorDescription, suggestion = "Vui lòng kiểm tra lại liên kết hoặc tệp âm thanh.") {
    return new EmbedBuilder()
      .setTitle(`❌ Có lỗi xảy ra: ${errorTitle}`)
      .setDescription(`\`\`\`\n${errorDescription}\n\`\`\``)
      .setColor(COLORS.ERROR)
      .addFields(
        { name: "💡 Gợi ý khắc phục", value: suggestion, inline: false }
      )
      .setFooter({ text: "Vitl Piano Bot • Error Diagnostics" })
      .setTimestamp();
  }
}
