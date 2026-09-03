/**
 * Dịch vụ thay đổi font chữ, hiệu ứng và dải màu (gradient) cho tên hiển thị của Bot qua Discord REST API v10.
 * Endpoint: PATCH https://discord.com/api/v10/guilds/{guild_id}/members/@me
 */

import { logger } from "../utils/logger.js";

export const FONT_NAMES = {
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
};

export const EFFECT_NAMES = {
  1: "None / Standard",
  2: "Neon Glow",
  3: "Gradient Flow",
  4: "Sparkle / Shimmer",
  5: "Shadow Outline",
  6: "Glitch / Pulse",
};

export const FONT_CHOICES = [
  { name: "1. Mặc định (Default)", value: 1 },
  { name: "2. Gothic / Old English (𝕲𝖔𝖙𝖍𝖎𝖈)", value: 2 },
  { name: "3. Cursive / Script (𝒞𝓊𝓇𝓈𝒾𝓋ℯ)", value: 3 },
  { name: "4. Bold Serif (𝐁𝐨𝐥𝐝 𝐒𝐞𝐫𝐢𝐟)", value: 4 },
  { name: "5. Monospace (𝙼𝚘𝚗𝚘𝚜𝚙𝚊𝚌𝚎)", value: 5 },
  { name: "6. Double Struck (𝔻𝕠𝕦𝕓𝕝𝕖 𝕊𝕥𝕣𝕦𝕔𝕜)", value: 6 },
  { name: "7. Sans Serif Bold (𝗦𝗮𝗻𝘀 𝗕𝗼𝗹𝗱)", value: 7 },
  { name: "8. Sans Serif Italic (𝘚𝘢𝘯𝘴 𝘐𝘵𝘢𝘭𝘪𝘤)", value: 8 },
  { name: "9. Serif Italic (𝑆𝑒𝑟𝑖𝑓 𝐼𝑡𝑎𝑙𝑖𝑐)", value: 9 },
  { name: "10. Fraktur (𝔉𝔯𝔞𝔨𝔱𝔲𝔯)", value: 10 },
  { name: "11. Fullwidth (Ｆｕｌｌｗｉｄｔｈ)", value: 11 },
  { name: "12. Small Caps (Sᴍᴀʟʟ Cᴀᴘs)", value: 12 },
];

export const EFFECT_CHOICES = [
  { name: "1. Tiêu chuẩn (None / Standard)", value: 1 },
  { name: "2. Neon Glow (Phát sáng Neon)", value: 2 },
  { name: "3. Gradient Flow (Dải màu chuyển động)", value: 3 },
  { name: "4. Sparkle / Shimmer (Lấp lánh)", value: 4 },
  { name: "5. Shadow Outline (Đổ bóng viền)", value: 5 },
  { name: "6. Glitch / Pulse (Xung nhịp)", value: 6 },
];

export const FONT_ALIAS_MAP = {
  default: 1,
  gothic: 2,
  oldenglish: 2,
  cursive: 3,
  script: 3,
  boldserif: 4,
  bold: 4,
  monospace: 5,
  mono: 5,
  doublestruck: 6,
  double: 6,
  sansbold: 7,
  sansserifbold: 7,
  sansitalic: 8,
  sansserifitalic: 8,
  italic: 8,
  serifitalic: 9,
  fraktur: 10,
  fullwidth: 11,
  wide: 11,
  smallcaps: 12,
  small: 12,
};

export const EFFECT_ALIAS_MAP = {
  none: 1,
  standard: 1,
  neon: 2,
  glow: 2,
  neonglow: 2,
  gradient: 3,
  flow: 3,
  gradientflow: 3,
  sparkle: 4,
  shimmer: 4,
  shadow: 5,
  outline: 5,
  glitch: 6,
  pulse: 6,
};

export function resolveFontId(fontInput) {
  if (fontInput === null || fontInput === undefined) return 1;
  if (typeof fontInput === "number") {
    return Math.max(1, Math.min(12, Math.floor(fontInput)));
  }
  const cleanStr = String(fontInput).toLowerCase().replace(/[^a-z0-9]/g, "");
  const parsedNum = parseInt(cleanStr, 10);
  if (!isNaN(parsedNum) && parsedNum >= 1 && parsedNum <= 12) {
    return parsedNum;
  }
  return FONT_ALIAS_MAP[cleanStr] || 1;
}

export function resolveEffectId(effectInput) {
  if (effectInput === null || effectInput === undefined) return 1;
  if (typeof effectInput === "number") {
    return Math.max(1, Math.min(6, Math.floor(effectInput)));
  }
  const cleanStr = String(effectInput).toLowerCase().replace(/[^a-z0-9]/g, "");
  const parsedNum = parseInt(cleanStr, 10);
  if (!isNaN(parsedNum) && parsedNum >= 1 && parsedNum <= 6) {
    return parsedNum;
  }
  return EFFECT_ALIAS_MAP[cleanStr] || 1;
}

/**
 * Chuyển đổi mã màu Hex (e.g. '#5865F2', 'EB459E') sang số nguyên Decimal.
 */
export function hexToDecimal(hexCode) {
  if (!hexCode) return 0;
  let cleanHex = String(hexCode).trim().replace(/^#/, "");
  if (cleanHex.toLowerCase().startsWith("0x")) {
    cleanHex = cleanHex.slice(2);
  }
  if (cleanHex.length === 3) {
    cleanHex = cleanHex.split("").map((c) => c + c).join("");
  }
  if (!/^[0-9a-fA-F]{6}$/.test(cleanHex)) {
    throw new Error(`Mã màu HEX không hợp lệ: '${hexCode}'.`);
  }
  return parseInt(cleanHex, 16);
}

/**
 * Phân tích chuỗi hoặc mảng màu HEX sang mảng tối đa 4 số Decimal.
 */
export function parseHexColors(hexInput) {
  if (!hexInput) {
    return [hexToDecimal("#5865F2"), hexToDecimal("#EB459E")];
  }

  let items = [];
  if (typeof hexInput === "string") {
    items = hexInput.split(/[,;\s]+/).map((s) => s.trim()).filter(Boolean);
  } else if (Array.isArray(hexInput)) {
    items = hexInput.map((s) => String(s).trim()).filter(Boolean);
  }

  const decimals = [];
  for (const it of items) {
    try {
      decimals.push(hexToDecimal(it));
    } catch (e) {
      logger.warn(`Bỏ qua mã màu không hợp lệ: ${it}`);
    }
  }

  if (decimals.length === 0) {
    return [hexToDecimal("#5865F2"), hexToDecimal("#EB459E")];
  }

  return decimals.slice(0, 4);
}

/**
 * Gọi Discord REST API để cập nhật Style Tên Bot.
 */
export async function updateBotNameStyle({
  client = null,
  guildId = null,
  fontId = 1,
  effectId = 1,
  hexColors = null,
  botToken = null,
} = {}) {
  const token = (botToken || process.env.DISCORD_BOT_TOKEN || "").trim();
  if (!token) {
    throw new Error("Chưa cấu hình DISCORD_BOT_TOKEN để gửi request tới Discord API.");
  }

  const safeFontId = resolveFontId(fontId);
  const safeEffectId = resolveEffectId(effectId);
  const colors = parseHexColors(hexColors);

  const payload = {
    display_name_font_id: safeFontId,
    display_name_effect_id: safeEffectId,
    display_name_colors: colors,
    display_name_styles: {
      font_id: safeFontId,
      effect_id: safeEffectId,
      colors: colors,
    },
  };

  const headers = {
    Authorization: `Bot ${token}`,
    "Content-Type": "application/json",
    "User-Agent": "DiscordBot (https://github.com/RandomGuy-VN/vitl-piano-transciber, 2.0.0)",
  };

  let targetGuildIds = [];
  if (guildId) {
    targetGuildIds = [String(guildId)];
  } else if (client && client.guilds && client.guilds.cache) {
    targetGuildIds = Array.from(client.guilds.cache.keys());
  } else if (process.env.GUILD_ID) {
    targetGuildIds = [process.env.GUILD_ID.trim()];
  }

  if (targetGuildIds.length === 0) {
    return {
      success: false,
      totalGuilds: 0,
      updatedCount: 0,
      failedCount: 0,
      details: "Không tìm thấy server nào để cập nhật style.",
      fontId: safeFontId,
      effectId: safeEffectId,
      colors: colors,
    };
  }

  logger.info(
    `Bắt đầu cập nhật style tên Bot (Font: ${safeFontId}, Effect: ${safeEffectId}) tới ${targetGuildIds.length} server(s)...`
  );

  const successGuilds = [];
  const failedGuilds = [];

  for (let i = 0; i < targetGuildIds.length; i++) {
    const gid = targetGuildIds[i];
    const endpoint = `https://discord.com/api/v10/guilds/${gid}/members/@me`;
    let retries = 0;
    const maxRetries = 3;

    while (retries < maxRetries) {
      try {
        const resp = await fetch(endpoint, {
          method: "PATCH",
          headers,
          body: JSON.stringify(payload),
        });

        if (resp.status === 200 || resp.status === 204) {
          logger.info(`-> [${i + 1}/${targetGuildIds.length}] Đã cập nhật thành công cho Guild: ${gid}`);
          successGuilds.push(gid);
          break;
        } else if (resp.status === 429) {
          retries++;
          let retryAfter = 1.5;
          try {
            const rData = await resp.json();
            retryAfter = Number(rData.retry_after) || 1.5;
          } catch {
            // ignore
          }
          logger.warn(`Rate limit 429 trên Guild ${gid}. Thử lại sau ${retryAfter}s (Lần ${retries}/${maxRetries})...`);
          await new Promise((r) => setTimeout(r, retryAfter * 1000));
          continue;
        } else if (resp.status === 401 || resp.status === 403) {
          const body = await resp.text();
          logger.warn(`Thiếu quyền trên Guild ${gid} (HTTP ${resp.status}): ${body}`);
          failedGuilds.push({ guildId: gid, status: resp.status, error: "Thiếu quyền hoặc bot chưa tham gia server." });
          break;
        } else {
          const body = await resp.text();
          logger.warn(`Lỗi cập nhật trên Guild ${gid} (HTTP ${resp.status}): ${body}`);
          failedGuilds.push({ guildId: gid, status: resp.status, error: body.slice(0, 150) });
          break;
        }
      } catch (err) {
        logger.error(`Lỗi kết nối khi cập nhật Guild ${gid}:`, err.message);
        failedGuilds.push({ guildId: gid, status: 0, error: err.message });
        break;
      }
    }

    if (targetGuildIds.length > 1) {
      await new Promise((r) => setTimeout(r, 300));
    }
  }

  const isSuccess = successGuilds.length > 0;

  return {
    success: isSuccess,
    totalGuilds: targetGuildIds.length,
    updatedCount: successGuilds.length,
    failedCount: failedGuilds.length,
    successGuilds,
    failedGuilds,
    fontId: safeFontId,
    fontName: FONT_NAMES[safeFontId] || `Font #${safeFontId}`,
    effectId: safeEffectId,
    effectName: EFFECT_NAMES[safeEffectId] || `Effect #${safeEffectId}`,
    colors,
    hexColors: colors.map((c) => `#${c.toString(16).padStart(6, "0").toUpperCase()}`),
  };
}
