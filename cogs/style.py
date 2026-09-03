"""
Cog quản lý Slash Command /setstyle và /fonts: Đổi font chữ, hiệu ứng và dải màu cho tên hiển thị của Bot.
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
    resolve_font_id,
    resolve_effect_id,
)

logger = logging.getLogger(__name__)

# Danh sách lựa chọn hiển thị trực quan trên Discord client
FONT_APP_CHOICES = [
    app_commands.Choice(name="1. Mặc định (Default)", value=1),
    app_commands.Choice(name="2. Gothic / Old English (𝕲𝖔𝖙𝖍𝖎𝖈)", value=2),
    app_commands.Choice(name="3. Cursive / Script (𝒞𝓊𝓇𝓈𝒾𝓋ℯ)", value=3),
    app_commands.Choice(name="4. Bold Serif (𝐁𝐨𝐥𝐝 𝐒𝐞𝐫𝐢𝐟)", value=4),
    app_commands.Choice(name="5. Monospace (𝙼𝚘𝚗𝚘𝚜𝚙𝚊𝚌𝚎)", value=5),
    app_commands.Choice(name="6. Double Struck (𝔻𝕠𝕦𝕓𝕝𝕖 𝕊𝕥𝕣𝕦𝕔𝕜)", value=6),
    app_commands.Choice(name="7. Sans Serif Bold (𝗦𝗮𝗻𝘀 𝗕𝗼𝗹𝗱)", value=7),
    app_commands.Choice(name="8. Sans Serif Italic (𝘚𝘢𝘯𝘴 𝘐𝘵𝘢𝘭𝘪𝘤)", value=8),
    app_commands.Choice(name="9. Serif Italic (𝑆𝑒𝑟𝑖𝑓 𝐼𝑡𝑎𝑙𝑖𝑐)", value=9),
    app_commands.Choice(name="10. Fraktur (𝔉𝔯𝔞𝔨𝔱𝔲𝔯)", value=10),
    app_commands.Choice(name="11. Fullwidth (Ｆｕｌｌｗｉｄｔｈ)", value=11),
    app_commands.Choice(name="12. Small Caps (Sᴍᴀʟʟ Cᴀᴘs)", value=12),
]

EFFECT_APP_CHOICES = [
    app_commands.Choice(name="1. Tiêu chuẩn (None / Standard)", value=1),
    app_commands.Choice(name="2. Neon Glow (Phát sáng Neon)", value=2),
    app_commands.Choice(name="3. Gradient Flow (Dải màu chuyển động)", value=3),
    app_commands.Choice(name="4. Sparkle / Shimmer (Lấp lánh)", value=4),
    app_commands.Choice(name="5. Shadow Outline (Đổ bóng viền)", value=5),
    app_commands.Choice(name="6. Glitch / Pulse (Xung nhịp)", value=6),
]


class StyleCog(commands.Cog):
    """Cog phụ trách tùy biến giao diện tên hiển thị của Bot trên Discord."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="fonts",
        description="Xem danh sách 12 kiểu Font chữ, 6 Hiệu ứng và các dải màu Gradient mẫu"
    )
    async def list_fonts(self, interaction: discord.Interaction) -> None:
        """Hiển thị bảng tra cứu font và hiệu ứng kèm mẫu hiển thị trực quan."""
        embed = discord.Embed(
            title="🎨 Bảng Tra Cứu Font Chữ & Hiệu Ứng Cho Bot",
            description="Sử dụng lệnh `/setstyle` cùng menu chọn kiểu chữ để tùy biến biệt danh hiển thị của Bot theo chuẩn Discord REST API v10.",
            color=discord.Color.from_rgb(88, 101, 242)
        )
        embed.add_field(
            name="🔤 12 Kiểu Font Chữ Hỗ Trợ (Fonts)",
            value=(
                "**1. Default**: `Vitl Piano Bot`\n"
                "**2. Gothic / Old English**: 𝔙𝔦𝔱𝔩 𝔓𝔦𝔞𝔫𝔬 𝔅𝔬𝔱\n"
                "**3. Cursive / Script**: 𝒱𝒾𝓉𝓁 𝒫𝒾𝒶𝓃𝑜 𝐵𝑜𝓉\n"
                "**4. Bold Serif**: 𝐕𝐢𝐭𝐥 𝐏𝐢𝐚𝐧𝐨 𝐁𝐨𝐭\n"
                "**5. Monospace**: 𝚅𝚒𝚝𝚕 𝙿𝚒𝚊𝚗𝚘 𝙱𝚘𝚝\n"
                "**6. Double Struck**: 𝕍𝕚𝕥𝕝 ℙ𝕚𝕒𝕟𝕠 𝔹𝕠𝕥\n"
                "**7. Sans Serif Bold**: 𝗩𝗶𝘁𝗹 𝗣𝗶𝗮𝗻𝗼 𝗕𝗼𝘁\n"
                "**8. Sans Serif Italic**: 𝘝𝘪𝘵𝘭 𝘗𝘪𝘢𝘯𝘰 𝘉𝘰𝘵\n"
                "**9. Serif Italic**: 𝑉𝑖𝑡𝑙 𝑃𝑖𝑎𝑛𝑜 𝐵𝑜𝑡\n"
                "**10. Fraktur**: 𝖁𝖎𝖙𝖑 𝕻𝖎𝖆𝖓𝖔 𝕭𝖔𝖙\n"
                "**11. Fullwidth**: Ｖｉｔｌ　Ｐｉａｎｏ　Ｂｏｔ\n"
                "**12. Small Caps**: Vɪᴛʟ Pɪᴀɴᴏ Bᴏᴛ"
            ),
            inline=False
        )
        embed.add_field(
            name="💫 6 Hiệu Ứng (Effects)",
            value=(
                "**1. Standard**: Tiêu chuẩn, không hiệu ứng\n"
                "**2. Neon Glow**: Phát sáng đèn Neon rực rỡ quanh chữ\n"
                "**3. Gradient Flow**: Chuyển tiếp màu mượt mà theo dải Gradient\n"
                "**4. Sparkle / Shimmer**: Hiệu ứng lấp lánh như kim cương\n"
                "**5. Shadow Outline**: Đổ bóng viền tương phản cao\n"
                "**6. Glitch / Pulse**: Hiệu ứng xung nhịp và sóng hiện đại"
            ),
            inline=False
        )
        embed.add_field(
            name="🎨 Gợi Ý Dải Màu Gradient Nổi Bật (Mã HEX)",
            value=(
                "• **Discord Blurple**: `#5865F2, #EB459E, #FEE75C`\n"
                "• **Cyberpunk Neon**: `#00FFAA, #FF00AA, #AA00FF`\n"
                "• **Sunset Warmth**: `#FF5500, #FFAA00, #FFFF00`\n"
                "• **Ocean Breeze**: `#00C0FF, #42E695, #3BB2B8`\n"
                "• **Royal Gold**: `#FFD700, #FFA500, #FF4500`"
            ),
            inline=False
        )
        embed.set_footer(text="Vitl Piano Bot • /setstyle [font] [effect] [colors]")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="setstyle",
        description="Đổi font chữ, hiệu ứng và dải màu (gradient) cho tên hiển thị của Bot"
    )
    @app_commands.describe(
        font="Chọn kiểu Font chữ hiển thị cho tên Bot",
        effect="Chọn hiệu ứng ánh sáng / chuyển động (Effect)",
        colors="Danh sách mã màu HEX (tối đa 4 màu, ví dụ: #5865F2, #EB459E, #FEE75C)",
        all_guilds="Áp dụng cho toàn bộ server bot tham gia (True) hoặc chỉ server hiện tại (False)"
    )
    @app_commands.choices(font=FONT_APP_CHOICES, effect=EFFECT_APP_CHOICES)
    async def set_style(
        self,
        interaction: discord.Interaction,
        font: Optional[app_commands.Choice[int]] = None,
        effect: Optional[app_commands.Choice[int]] = None,
        colors: Optional[str] = "#5865F2, #EB459E",
        all_guilds: bool = True,
        font_id: Optional[int] = None,
        effect_id: Optional[int] = None,
    ) -> None:
        """Thực thi cập nhật style tên bot theo yêu cầu của quản trị viên."""
        # 1. Kiểm tra quyền hạn
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

        # 2. Defer phản hồi (Ephemeral)
        await interaction.response.defer(ephemeral=True, thinking=True)

        chosen_font_id = font.value if font else (font_id or 1)
        chosen_effect_id = effect.value if effect else (effect_id or 1)
        target_guild_id = None if all_guilds else (interaction.guild_id if interaction.guild else None)

        try:
            result = await update_bot_name_style(
                bot=self.bot,
                guild_id=target_guild_id,
                font_id=chosen_font_id,
                effect_id=chosen_effect_id,
                hex_colors=colors
            )

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
