"""
Dịch vụ thay đổi font chữ, hiệu ứng (glowing/effect) và dải màu gradient cho tên hiển thị của Discord Bot.
Sử dụng Discord REST API v10 endpoint: PATCH /users/@me/guilds/{guild_id}/member
"""

import asyncio
import logging
import re
from typing import Optional, List, Dict, Any, Union
import aiohttp
import discord

from config import DISCORD_BOT_TOKEN

logger = logging.getLogger(__name__)

# Danh sách tên hiệu ứng và font chữ trực quan để hiển thị cho người dùng
FONT_NAMES: Dict[int, str] = {
    1: "Default Font",
    2: "Gothic / Old English",
    3: "Cursive / Script",
    4: "Bold Serif",
    5: "Monospace",
    6: "Double Struck",
    7: "Sans Serif Bold",
    8: "Sans Serif Italic",
    9: "Serif Italic",
    10: "Fraktur",
    11: "Fullwidth",
    12: "Small Caps",
}

EFFECT_NAMES: Dict[int, str] = {
    1: "None / Standard",
    2: "Neon Glow",
    3: "Gradient Flow",
    4: "Sparkle / Shimmer",
    5: "Shadow Outline",
    6: "Glitch / Pulse",
}


def hex_to_decimal(hex_code: str) -> int:
    """
    Chuyển đổi mã màu Hex (ví dụ: '#5865F2', 'EB459E', '0xFFFFFF') sang số nguyên thập phân (Decimal).

    Args:
        hex_code (str): Chuỗi mã màu HEX.

    Returns:
        int: Giá trị màu Decimal tương ứng.
    """
    clean_hex = hex_code.strip().lstrip("#")
    if clean_hex.lower().startswith("0x"):
        clean_hex = clean_hex[2:]

    # Hỗ trợ dạng rút gọn 3 ký tự (ví dụ: 'FFF' -> 'FFFFFF')
    if len(clean_hex) == 3:
        clean_hex = "".join([c * 2 for c in clean_hex])

    # Kiểm tra tính hợp lệ của chuỗi hex
    if not re.fullmatch(r"^[0-9a-fA-F]{6}$", clean_hex):
        raise ValueError(f"Mã màu HEX không hợp lệ: '{hex_code}'. Định dạng chuẩn: '#RRGGBB' (ví dụ: '#5865F2').")

    return int(clean_hex, 16)


def parse_hex_colors(hex_input: Union[List[str], str, None]) -> List[int]:
    """
    Xử lý và chuyển đổi danh sách mã màu HEX sang mảng Decimal colors (tối đa 4 màu).

    Args:
        hex_input (Union[List[str], str, None]): Danh sách màu hoặc chuỗi phân tách bởi dấu phẩy/khoảng trắng.

    Returns:
        List[int]: Danh sách tối đa 4 số nguyên thập phân đại diện cho màu.
    """
    if not hex_input:
        # Màu mặc định: Xanh Discord Blurple + Hồng Neon
        return [hex_to_decimal("#5865F2"), hex_to_decimal("#EB459E")]

    raw_items: List[str] = []
    if isinstance(hex_input, str):
        # Tách chuỗi theo dấu phẩy, khoảng trắng hoặc chấm phẩy
        parts = re.split(r"[,;\s]+", hex_input.strip())
        raw_items = [p for p in parts if p]
    elif isinstance(hex_input, list):
        raw_items = [str(item).strip() for item in hex_input if item]

    decimal_colors: List[int] = []
    for item in raw_items:
        try:
            decimal_colors.append(hex_to_decimal(item))
        except ValueError as err:
            logger.warning("Bỏ qua mã màu không hợp lệ: %s (%s)", item, err)

    if not decimal_colors:
        decimal_colors = [hex_to_decimal("#5865F2"), hex_to_decimal("#EB459E")]

    # Giới hạn tối đa 4 màu theo quy chuẩn Discord API
    return decimal_colors[:4]


async def update_bot_name_style(
    bot: Optional[discord.Client] = None,
    guild_id: Optional[int] = None,
    font_id: int = 1,
    effect_id: int = 1,
    hex_colors: Union[List[str], str, None] = None,
    bot_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Cập nhật font chữ, hiệu ứng và dải màu (gradient) cho tên hiển thị của bot.

    Args:
        bot (Optional[discord.Client]): Đối tượng bot Discord.
        guild_id (Optional[int]): ID của server muốn áp dụng. Nếu None, lặp qua toàn bộ bot.guilds.
        font_id (int): ID kiểu chữ (1-12).
        effect_id (int): ID hiệu ứng (1-6).
        hex_colors (Union[List[str], str, None]): Danh sách mã màu Hex (tối đa 4 màu).
        bot_token (Optional[str]): Token của bot (nếu không truyền sẽ lấy DISCORD_BOT_TOKEN từ config).

    Returns:
        Dict[str, Any]: Kết quả chi tiết quá trình cập nhật.
    """
    token = (bot_token or DISCORD_BOT_TOKEN).strip()
    if not token:
        raise ValueError("Chưa cung cấp Discord Bot Token để thực hiện request.")

    # 1. Chuẩn hóa font_id và effect_id
    font_id = max(1, min(12, int(font_id)))
    effect_id = max(1, min(6, int(effect_id)))
    colors = parse_hex_colors(hex_colors)

    # 2. Chuẩn bị payload và headers theo chuẩn Discord REST API v10
    payload = {
        "display_name_styles": {
            "font_id": font_id,
            "effect_id": effect_id,
            "colors": colors
        }
    }

    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": "DiscordBot (https://github.com/RandomGuy-VN/vitl-piano-transciber, 1.0.0)"
    }

    # 3. Xác định danh sách Guild IDs cần cập nhật
    target_guild_ids: List[int] = []
    if guild_id is not None:
        target_guild_ids = [int(guild_id)]
    elif bot and bot.guilds:
        target_guild_ids = [g.id for g in bot.guilds]
    else:
        logger.warning("Không có guild nào để cập nhật style tên bot.")
        return {
            "success": False,
            "total_guilds": 0,
            "updated_count": 0,
            "failed_count": 0,
            "details": "Không tìm thấy server nào để cập nhật.",
            "font_id": font_id,
            "effect_id": effect_id,
            "colors": colors,
        }

    logger.info(
        "Bắt đầu cập nhật style tên Bot (Font: %d, Effect: %d, Colors: %s) tới %d servers...",
        font_id, effect_id, [f"#{c:06X}" for c in colors], len(target_guild_ids)
    )

    success_guilds: List[int] = []
    failed_guilds: List[Dict[str, Any]] = []

    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for idx, gid in enumerate(target_guild_ids, start=1):
            endpoint = f"https://discord.com/api/v10/users/@me/guilds/{gid}/member"
            retries = 0
            max_retries = 3
            updated = False

            while retries < max_retries:
                try:
                    async with session.patch(endpoint, json=payload, headers=headers) as resp:
                        if resp.status in (200, 204):
                            logger.info("-> [%d/%d] Đã cập nhật thành công cho Guild ID: %d", idx, len(target_guild_ids), gid)
                            success_guilds.append(gid)
                            updated = True
                            break

                        elif resp.status == 429:
                            # Xử lý Rate limit từ Discord API
                            retries += 1
                            retry_after = 1.5
                            try:
                                rate_data = await resp.json()
                                retry_after = float(rate_data.get("retry_after", 1.5))
                            except Exception:
                                pass
                            logger.warning(
                                "Rate limit HTTP 429 trên Guild %d. Thử lại sau %.2fs (Lần %d/%d)...",
                                gid, retry_after, retries, max_retries
                            )
                            await asyncio.sleep(retry_after)
                            continue

                        elif resp.status in (401, 403):
                            # Lỗi thiếu quyền hoặc token không hợp lệ
                            err_msg = await resp.text()
                            logger.warning("Không có quyền cập nhật tên trên Guild ID %d (HTTP %d): %s", gid, resp.status, err_msg)
                            failed_guilds.append({
                                "guild_id": gid,
                                "status": resp.status,
                                "error": "Thiếu quyền quản lý biệt danh hoặc bot chưa ở trong server."
                            })
                            break

                        else:
                            err_msg = await resp.text()
                            logger.warning("Lỗi cập nhật tên trên Guild ID %d (HTTP %d): %s", gid, resp.status, err_msg)
                            failed_guilds.append({
                                "guild_id": gid,
                                "status": resp.status,
                                "error": err_msg[:200]
                            })
                            break

                except Exception as req_exc:
                    logger.exception("Lỗi kết nối khi gửi request style tới Guild ID %d: %s", gid, req_exc)
                    failed_guilds.append({
                        "guild_id": gid,
                        "status": 0,
                        "error": str(req_exc)
                    })
                    break

            # Độ trễ nhẹ giữa các request để bảo vệ rate limit
            if len(target_guild_ids) > 1:
                await asyncio.sleep(0.3)

    is_overall_success = len(success_guilds) > 0

    return {
        "success": is_overall_success,
        "total_guilds": len(target_guild_ids),
        "updated_count": len(success_guilds),
        "failed_count": len(failed_guilds),
        "success_guilds": success_guilds,
        "failed_guilds": failed_guilds,
        "font_id": font_id,
        "font_name": FONT_NAMES.get(font_id, f"Font #{font_id}"),
        "effect_id": effect_id,
        "effect_name": EFFECT_NAMES.get(effect_id, f"Effect #{effect_id}"),
        "colors": colors,
        "hex_colors": [f"#{c:06X}" for c in colors],
    }
