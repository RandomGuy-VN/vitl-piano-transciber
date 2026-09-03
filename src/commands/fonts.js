/**
 * Lệnh Slash /fonts: Hiển thị bảng tra cứu 12 Font chữ, 6 Hiệu ứng và các bộ màu Gradient mẫu cho tên Bot.
 */

import { SlashCommandBuilder, EmbedBuilder } from "discord.js";

export const data = new SlashCommandBuilder()
  .setName("fonts")
  .setDescription("Xem danh sách 12 kiểu Font chữ, 6 Hiệu ứng và các dải màu Gradient mẫu");

export async function execute(interaction) {
  const embed = new EmbedBuilder()
    .setTitle("🎨 Bảng Tra Cứu Font Chữ & Hiệu Ứng Cho Bot")
    .setDescription(
      "Sử dụng lệnh `/setstyle` cùng menu chọn kiểu chữ để tùy biến biệt danh hiển thị của Bot theo chuẩn Discord REST API v10."
    )
    .setColor(0x5865F2)
    .addFields(
      {
        name: "🔤 12 Kiểu Font Chữ Hỗ Trợ (Fonts)",
        value:
          "**1. Default**: `Vitl Piano Bot`\n" +
          "**2. Gothic / Old English**: 𝔙𝔦𝔱𝔩 𝔓𝔦𝔞𝔫𝔬 𝔅𝔬𝔱\n" +
          "**3. Cursive / Script**: 𝒱𝒾𝓉𝓁 𝒫𝒾𝒶𝓃𝑜 𝐵𝑜𝓉\n" +
          "**4. Bold Serif**: 𝐕𝐢𝐭𝐥 𝐏𝐢𝐚𝐧𝐨 𝐁𝐨𝐭\n" +
          "**5. Monospace**: 𝚅𝚒𝚝𝚕 𝙿𝚒𝚊𝚗𝚘 𝙱𝚘𝚝\n" +
          "**6. Double Struck**: 𝕍𝕚𝕥𝕝 ℙ𝕚𝕒𝕟𝕠 𝔹𝕠𝕥\n" +
          "**7. Sans Serif Bold**: 𝗩𝗶𝘁𝗹 𝗣𝗶𝗮𝗻𝗼 𝗕𝗼𝘁\n" +
          "**8. Sans Serif Italic**: 𝘝𝘪𝘵𝘭 𝘗𝘪𝘢𝘯𝘰 𝘉𝘰𝘵\n" +
          "**9. Serif Italic**: 𝑉𝑖𝑡𝑙 𝑃𝑖𝑎𝑛𝑜 𝐵𝑜𝑡\n" +
          "**10. Fraktur**: 𝖁𝖎𝖙𝖑 𝕻𝖎𝖆𝖓𝖔 𝕭𝖔𝖙\n" +
          "**11. Fullwidth**: Ｖｉｔｌ　Ｐｉａｎｏ　Ｂｏｔ\n" +
          "**12. Small Caps**: Vɪᴛʟ Pɪᴀɴᴏ Bᴏᴛ",
        inline: false,
      },
      {
        name: "💫 6 Hiệu Ứng (Effects)",
        value:
          "**1. Standard**: Tiêu chuẩn, không hiệu ứng\n" +
          "**2. Neon Glow**: Phát sáng đèn Neon rực rỡ quanh chữ\n" +
          "**3. Gradient Flow**: Chuyển tiếp màu mượt mà theo dải Gradient\n" +
          "**4. Sparkle / Shimmer**: Hiệu ứng lấp lánh như kim cương\n" +
          "**5. Shadow Outline**: Đổ bóng viền tương phản cao\n" +
          "**6. Glitch / Pulse**: Hiệu ứng xung nhịp và sóng hiện đại",
        inline: false,
      },
      {
        name: "🎨 Gợi Ý Dải Màu Gradient Nổi Bật (Mã HEX)",
        value:
          "• **Discord Blurple**: `#5865F2, #EB459E, #FEE75C`\n" +
          "• **Cyberpunk Neon**: `#00FFAA, #FF00AA, #AA00FF`\n" +
          "• **Sunset Warmth**: `#FF5500, #FFAA00, #FFFF00`\n" +
          "• **Ocean Breeze**: `#00C0FF, #42E695, #3BB2B8`\n" +
          "• **Royal Gold**: `#FFD700, #FFA500, #FF4500`",
        inline: false,
      }
    )
    .setFooter({ text: "Vitl Piano Bot • /setstyle [font] [effect] [colors]" })
    .setTimestamp();

  await interaction.reply({ embeds: [embed], ephemeral: true });
}
