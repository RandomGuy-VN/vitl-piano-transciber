"""
Cog quản lý Slash Command /setstyle: Đổi font chữ, hiệu ứng và dải màu cho tên hiển thị của Bot.
Chỉ dành riêng cho Quản trị viên (Admin) hoặc Bot Owner.
"""

import logging
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands

from services.style_service import (
    update_bot_name_style,
    FONT_NAMES,
    EFFECT_NAMES,
    parse_hex_colors,
)

logger = logging.getLogger(__name__)


class StyleCog(commands.Cog):
    """Cog phụ trách tùy biến giao diện tên hiển thị của Bot trên Discord."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="setstyle",
        description="Đổi font chữ, hiệu ứng và dải màu (gradient) cho tên hiển thị của Bot"
    )
    @app_commands.describe(
        font_id="ID Font chữ (1-12: Default, Gothic, Cursive, Bold, Monospace, v.v.)",
        effect_id="ID Hiệu ứng (1: Không, 2: Neon Glow, 3: Gradient Flow, 4: Sparkle, 5: Shadow, 6: Glitch)",
        colors="Danh sách mã màu HEX (tối đa 4 màu, ví dụ: #5865F2, #EB459E, #FEE75C)",
        all_guilds="Áp dụng cho toàn bộ server bot tham gia (True) hoặc chỉ server hiện tại (False)"
    )
    async def set_style(
        self,
        interaction: discord.Interaction,
        font_id: app_commands.Range[int, 1, 12] = 1,
        effect_id: app_commands.Range[int, 1, 6] = 1,
        colors: Optional[str] = "#5865F2, #EB459E",
        all_guilds: bool = True
    ) -> None:
        """Thực thi cập nhật style tên bot theo yêu cầu của quản trị viên."""
        # ==========================================
        # 1. KIỂM TRA QUYỀN HẠN (ADMIN HOẶC BOT OWNER)
        # ==========================================
        is_admin = False
        if interaction.guild and isinstance(interaction.user, discord.Member):
            is_admin = interaction.user.guild_permissions.administrator

        is_owner = await self.bot.is_owner(interaction.user)

        if not is_admin and not is_owner:
            err_embed = discord.Embed(
                title="⛔ Không có quyền thực hiện",
                description="Lệnh này chỉ dành riêng cho **Quản trị viên Server (Administrator)** hoặc **Chủ sở hữu Bot (Bot Owner)**.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=err_embed, ephemeral=True)
            return

        # ==========================================
        # 2. DEFER PHẢN HỒI (EPHEMERAL)
        # ==========================================
        await interaction.response.defer(ephemeral=True, thinking=True)

        target_guild_id = None if all_guilds else (interaction.guild_id if interaction.guild else None)

        try:
            # 3. Gọi hàm cập nhật style
            result = await update_bot_name_style(
                bot=self.bot,
                guild_id=target_guild_id,
                font_id=font_id,
                effect_id=effect_id,
                hex_colors=colors
            )

            # 4. Xây dựng Embed phản hồi trực quan
            if result.get("success"):
                embed = discord.Embed(
                    title="✨ Cập nhật Style Tên Bot thành công!",
                    description="Tên hiển thị của Bot đã được đồng bộ với phong cách hiển thị mới theo Discord Display Name Styles API.",
                    color=discord.Color.from_rgb(88, 101, 242)
                )

                font_name = FONT_NAMES.get(font_id, f"Font #{font_id}")
                effect_name = EFFECT_NAMES.get(effect_id, f"Effect #{effect_id}")
                hex_list_str = " ➔ ".join([f"`{c}`" for c in result.get("hex_colors", [])])

                embed.add_field(name="🔤 Kiểu chữ (Font)", value=f"**{font_name}** *(ID: {font_id})*", inline=True)
                embed.add_field(name="💫 Hiệu ứng (Effect)", value=f"**{effect_name}** *(ID: {effect_id})*", inline=True)
                embed.add_field(name="🎨 Dải màu (Gradient Colors)", value=hex_list_str or "`Mặc định`", inline=False)

                updated_cnt = result.get("updated_count", 0)
                total_cnt = result.get("total_guilds", 0)
                embed.add_field(
                    name="🌐 Phạm vi áp dụng",
                    value=f"Đã cập nhật trên **{updated_cnt}/{total_cnt}** máy chủ Discord.",
                    inline=False
                )

                if result.get("failed_count", 0) > 0:
                    embed.add_field(
                        name="⚠️ Ghi chú",
                        value=f"Có {result['failed_count']} server không thể cập nhật (do thiếu quyền quản lý biệt danh).",
                        inline=False
                    )

                embed.set_footer(text="Vitl Piano Bot • Discord Display Name Styles v10")
                await interaction.edit_original_response(embed=embed)

            else:
                embed = discord.Embed(
                    title="❌ Cập nhật thất bại",
                    description=f"Không thể cập nhật style tên Bot.\nChi tiết: `{result.get('details', 'Lỗi không xác định từ Discord API')}`",
                    color=discord.Color.red()
                )
                await interaction.edit_original_response(embed=embed)

        except Exception as exc:
            logger.exception("Lỗi khi thực thi lệnh /setstyle: %s", exc)
            err_embed = discord.Embed(
                title="❌ Đã xảy ra lỗi",
                description=f"```{str(exc)}```",
                color=discord.Color.red()
            )
            await interaction.edit_original_response(embed=err_embed)


async def setup(bot: commands.Bot) -> None:
    """Hàm đăng ký Cog vào Discord Bot."""
    await bot.add_cog(StyleCog(bot))
