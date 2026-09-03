/**
 * Lệnh Slash /setstyle: Tùy biến font chữ, hiệu ứng và dải màu (gradient) cho tên hiển thị của Bot.
 * Dành riêng cho Quản trị viên (Administrator) hoặc Bot Owner.
 */

import { SlashCommandBuilder, PermissionsBitField, EmbedBuilder } from "discord.js";
import { updateBotNameStyle, FONT_NAMES, EFFECT_NAMES } from "../services/styleService.js";
import { logger } from "../utils/logger.js";

export const data = new SlashCommandBuilder()
  .setName("setstyle")
  .setDescription("Đổi font chữ, hiệu ứng và dải màu (gradient) cho tên hiển thị của Bot")
  .addIntegerOption((option) =>
    option
      .setName("font_id")
      .setDescription("ID Kiểu chữ (1-12: Default, Gothic, Cursive, Bold, Monospace, v.v.)")
      .setMinValue(1)
      .setMaxValue(12)
      .setRequired(false)
  )
  .addIntegerOption((option) =>
    option
      .setName("effect_id")
      .setDescription("ID Hiệu ứng (1: Không, 2: Neon Glow, 3: Gradient Flow, 4: Sparkle, 5: Shadow, 6: Glitch)")
      .setMinValue(1)
      .setMaxValue(6)
      .setRequired(false)
  )
  .addStringOption((option) =>
    option
      .setName("colors")
      .setDescription("Danh sách mã màu HEX (tối đa 4 màu, ví dụ: #5865F2, #EB459E, #FEE75C)")
      .setRequired(false)
  )
  .addBooleanOption((option) =>
    option
      .setName("all_guilds")
      .setDescription("Áp dụng cho toàn bộ server (True) hoặc chỉ server hiện tại (False)")
      .setRequired(false)
  );

export async function execute(interaction) {
  // 1. Kiểm tra quyền hạn
  const isOwner = interaction.client.application?.owner
    ? (interaction.client.application.owner.id === interaction.user.id)
    : false;

  const isAdmin = interaction.memberPermissions?.has(PermissionsBitField.Flags.Administrator);

  if (!isAdmin && !isOwner) {
    const noPermEmbed = new EmbedBuilder()
      .setTitle("⛔ Không có quyền thực hiện")
      .setDescription("Lệnh này chỉ dành riêng cho **Quản trị viên (Administrator)** hoặc **Chủ sở hữu Bot**.")
      .setColor(0xE74C3C);
    return await interaction.reply({ embeds: [noPermEmbed], ephemeral: true });
  }

  // 2. Defer phản hồi dạng riêng tư (Ephemeral)
  await interaction.deferReply({ ephemeral: true });

  const fontId = interaction.options.getInteger("font_id") || 1;
  const effectId = interaction.options.getInteger("effect_id") || 1;
  const colors = interaction.options.getString("colors") || "#5865F2, #EB459E";
  const allGuilds = interaction.options.getBoolean("all_guilds") ?? true;

  const targetGuildId = allGuilds ? null : interaction.guildId;

  try {
    const result = await updateBotNameStyle({
      client: interaction.client,
      guildId: targetGuildId,
      fontId,
      effectId,
      hexColors: colors,
    });

    if (result.success) {
      const fontName = FONT_NAMES[fontId] || `Font #${fontId}`;
      const effectName = EFFECT_NAMES[effectId] || `Effect #${effectId}`;
      const hexListStr = result.hexColors.map((c) => `\`${c}\``).join(" ➔ ");

      const embed = new EmbedBuilder()
        .setTitle("✨ Cập nhật Style Tên Bot thành công!")
        .setDescription("Tên hiển thị của Bot đã được đồng bộ với phong cách hiển thị mới theo Discord REST API v10.")
        .setColor(0x5865F2)
        .addFields(
          { name: "🔤 Kiểu chữ (Font)", value: `**${fontName}** *(ID: ${fontId})*`, inline: true },
          { name: "💫 Hiệu ứng (Effect)", value: `**${effectName}** *(ID: ${effectId})*`, inline: true },
          { name: "🎨 Dải màu (Gradient)", value: hexListStr || "`Mặc định`", inline: false },
          {
            name: "🌐 Phạm vi áp dụng",
            value: `Đã cập nhật trên **${result.updatedCount}/${result.totalGuilds}** máy chủ Discord.`,
            inline: false,
          }
        )
        .setFooter({ text: "Vitl Piano Bot • Node.js Discord REST API v10" })
        .setTimestamp();

      if (result.failedCount > 0) {
        embed.addFields({
          name: "⚠️ Ghi chú",
          value: `Có ${result.failedCount} server không thể cập nhật (do bot chưa có quyền trong server đó).`,
          inline: false,
        });
      }

      await interaction.editReply({ embeds: [embed] });
    } else {
      const failEmbed = new EmbedBuilder()
        .setTitle("❌ Cập nhật thất bại")
        .setDescription(`Không thể cập nhật style tên Bot.\nChi tiết: \`${result.details || "Lỗi từ Discord API"}\``)
        .setColor(0xE74C3C);
      await interaction.editReply({ embeds: [failEmbed] });
    }
  } catch (err) {
    logger.error("Lỗi khi chạy lệnh /setstyle:", err);
    const errEmbed = new EmbedBuilder()
      .setTitle("❌ Đã xảy ra lỗi")
      .setDescription(`\`\`\`\n${err.message}\n\`\`\``)
      .setColor(0xE74C3C);
    await interaction.editReply({ embeds: [errEmbed] });
  }
}
