/**
 * Bộ kiểm thử đơn vị tự động cho Node.js Discord Bot (sử dụng node:test).
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  formatBytes,
  formatDuration,
  formatElapsedTime,
  sanitizeFilename,
  isSpotifyUrl,
  isYoutubeUrl,
  detectSourceName,
} from "../src/utils/helpers.js";
import {
  hexToDecimal,
  parseHexColors,
  resolveFontId,
  resolveEffectId,
  FONT_CHOICES,
  EFFECT_CHOICES,
} from "../src/services/styleService.js";
import { DiscordEmbedBuilder, COLORS } from "../src/services/embedBuilder.js";
import * as transcriptCmd from "../src/commands/transcript.js";
import * as setstyleCmd from "../src/commands/setstyle.js";
import * as fontsCmd from "../src/commands/fonts.js";

test("Helpers: formatBytes", () => {
  assert.equal(formatBytes(500), "500.00 B");
  assert.equal(formatBytes(1024), "1.00 KB");
  assert.equal(formatBytes(1024 * 1024 * 2.5), "2.50 MB");
  assert.equal(formatBytes(-5), "0 B");
});

test("Helpers: formatDuration", () => {
  assert.equal(formatDuration(45), "00:45");
  assert.equal(formatDuration(125), "02:05");
  assert.equal(formatDuration(3665), "01:01:05");
  assert.equal(formatDuration(null), "Không rõ");
  assert.equal(formatDuration(-1), "Không rõ");
});

test("Helpers: formatElapsedTime", () => {
  assert.equal(formatElapsedTime(12.34), "12.3s");
  assert.equal(formatElapsedTime(85.2), "1m 25.2s");
  assert.equal(formatElapsedTime(-1), "0.0s");
});

test("Helpers: sanitizeFilename", () => {
  assert.equal(sanitizeFilename("Chopin: Nocturne Op. 9?"), "Chopin Nocturne Op. 9");
  assert.equal(sanitizeFilename("A".repeat(100), 50).length, 50);
  assert.equal(sanitizeFilename("   "), "transcription");
});

test("Helpers: URL Detection", () => {
  assert.equal(isSpotifyUrl("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT"), true);
  assert.equal(isSpotifyUrl("https://youtu.be/example"), false);

  assert.equal(isYoutubeUrl("https://www.youtube.com/watch?v=123"), true);
  assert.equal(isYoutubeUrl("https://youtu.be/123"), true);
  assert.equal(isYoutubeUrl("https://spotify.com"), false);

  assert.equal(detectSourceName("https://youtu.be/123"), "YouTube");
  assert.equal(detectSourceName("https://open.spotify.com/track/123"), "Spotify");
  assert.equal(detectSourceName("https://soundcloud.com/song"), "SoundCloud");
  assert.equal(detectSourceName(""), "Tệp tải lên");
});

test("StyleService: hexToDecimal & parseHexColors", () => {
  assert.equal(hexToDecimal("#5865F2"), 5793266);
  assert.equal(hexToDecimal("FFFFFF"), 16777215);
  assert.equal(hexToDecimal("FFF"), 16777215);
  assert.throws(() => hexToDecimal("invalid"), /Mã màu HEX không hợp lệ/);

  const parsed = parseHexColors("#5865F2, #EB459E, #FEE75C");
  assert.equal(parsed.length, 3);
  assert.equal(parsed[0], 5793266);

  // Giới hạn 4 màu
  const parsed5 = parseHexColors("#111111, #222222, #333333, #444444, #555555");
  assert.equal(parsed5.length, 4);

  // Fallback
  const fallback = parseHexColors(null);
  assert.equal(fallback.length, 2);
});

test("StyleService: resolveFontId & resolveEffectId & choices", () => {
  assert.equal(FONT_CHOICES.length, 12);
  assert.equal(EFFECT_CHOICES.length, 6);

  // Numeric
  assert.equal(resolveFontId(5), 5);
  assert.equal(resolveFontId(99), 12);
  assert.equal(resolveFontId(-1), 1);

  // String aliases
  assert.equal(resolveFontId("monospace"), 5);
  assert.equal(resolveFontId("gothic"), 2);
  assert.equal(resolveFontId("cursive"), 3);
  assert.equal(resolveFontId("bold"), 4);
  assert.equal(resolveFontId("unknown"), 1);

  // Effect resolver
  assert.equal(resolveEffectId(2), 2);
  assert.equal(resolveEffectId("neon"), 2);
  assert.equal(resolveEffectId("gradient"), 3);
  assert.equal(resolveEffectId("glitch"), 6);
  assert.equal(resolveEffectId("invalid"), 1);
});

test("EmbedBuilder: generates valid Embeds", () => {
  const queued = DiscordEmbedBuilder.createQueuedEmbed("Song.mp3", "Tệp tải lên", 1, 1);
  assert.equal(queued.data.color, COLORS.QUEUED);
  assert.ok(queued.data.title.includes("hàng chờ"));

  const downloading = DiscordEmbedBuilder.createDownloadingEmbed("https://youtu.be/123", "YouTube");
  assert.equal(downloading.data.color, COLORS.DOWNLOADING);

  const processing = DiscordEmbedBuilder.createProcessingEmbed("Moonlight", 180, "RTX 3050", true);
  assert.equal(processing.data.color, COLORS.PROCESSING);

  const success = DiscordEmbedBuilder.createSuccessEmbed("Moonlight", 15000, 180, 12.5, "RTX 3050");
  assert.equal(success.data.color, COLORS.SUCCESS);

  const error = DiscordEmbedBuilder.createErrorEmbed("Lỗi", "Chi tiết lỗi");
  assert.equal(error.data.color, COLORS.ERROR);
});

test("Commands: Slash commands definition integrity", () => {
  assert.equal(transcriptCmd.data.name, "transcript");
  assert.equal(typeof transcriptCmd.execute, "function");

  assert.equal(setstyleCmd.data.name, "setstyle");
  assert.equal(typeof setstyleCmd.execute, "function");

  assert.equal(fontsCmd.data.name, "fonts");
  assert.equal(typeof fontsCmd.execute, "function");
});
