/**
 * Bộ kiểm thử đơn vị tự động cho Node.js Discord Bot (sử dụng node:test).
 */

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";

import {
  formatBytes,
  formatDuration,
  formatElapsedTime,
  sanitizeFilename,
  isSpotifyUrl,
  isYoutubeUrl,
  isSoundcloudUrl,
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
import {
  getConfig,
  getEnvDefaults,
  loadConfig,
  resetConfigCache,
  sanitizeConfig,
  saveConfig,
} from "../src/services/configStore.js";
import {
  LoginThrottle,
  SessionStore,
  createPanelRouter,
  safeCompare,
} from "../src/services/webPanel.js";
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

  assert.equal(isSoundcloudUrl("https://soundcloud.com/artist/song"), true);
  assert.equal(isSoundcloudUrl("https://on.soundcloud.com/xyz123"), true);
  assert.equal(isSoundcloudUrl("https://youtube.com"), false);

  assert.equal(detectSourceName("https://youtu.be/123"), "YouTube");
  assert.equal(detectSourceName("https://open.spotify.com/track/123"), "Spotify");
  assert.equal(detectSourceName("https://soundcloud.com/song"), "SoundCloud");
  assert.equal(detectSourceName("https://on.soundcloud.com/abc"), "SoundCloud");
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

async function withTempConfig(run) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "vitl-panel-"));
  const previousPath = process.env.BOT_CONFIG_PATH;
  process.env.BOT_CONFIG_PATH = path.join(tempDir, "bot-config.json");
  resetConfigCache();

  try {
    return await run(process.env.BOT_CONFIG_PATH);
  } finally {
    if (previousPath === undefined) delete process.env.BOT_CONFIG_PATH;
    else process.env.BOT_CONFIG_PATH = previousPath;
    resetConfigCache();
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
}

test("ConfigStore: sanitize chuẩn hóa giá trị hợp lệ", () => {
  const { config, errors } = sanitizeConfig({
    defaultFontId: "5",
    defaultNameColors: "#fff, EB459E",
    device: "CUDA",
    enableAutoStyle: "false",
    maxConcurrentJobs: 3,
  });

  assert.deepEqual(errors, []);
  assert.equal(config.defaultFontId, 5);
  assert.equal(config.defaultNameColors, "#FFFFFF, #EB459E");
  assert.equal(config.device, "cuda");
  assert.equal(config.enableAutoStyle, false);
  assert.equal(config.maxConcurrentJobs, 3);
});

test("ConfigStore: sanitize từ chối giá trị sai", () => {
  const { errors } = sanitizeConfig({
    defaultFontId: 99,
    defaultEffectId: 0,
    defaultNameColors: "#5865F2, notacolor",
    device: "tpu",
    maxAudioDurationSeconds: 5,
    unknownField: "x",
  });

  const fields = errors.map((error) => error.field).sort();
  assert.deepEqual(fields, [
    "defaultEffectId",
    "defaultFontId",
    "defaultNameColors",
    "device",
    "maxAudioDurationSeconds",
    "unknownField",
  ]);
});

test("ConfigStore: sanitize giới hạn tối đa 4 mã màu", () => {
  const { errors } = sanitizeConfig({
    defaultNameColors: "#111111, #222222, #333333, #444444, #555555",
  });
  assert.equal(errors.length, 1);
  assert.match(errors[0].message, /tối đa 4 mã màu/);
});

test("ConfigStore: lưu và nạp lại cấu hình từ đĩa", async () => {
  await withTempConfig((configPath) => {
    const result = saveConfig({ defaultFontId: 7, activityText: "Piano 24/7" });
    assert.equal(result.ok, true);
    assert.equal(result.config.defaultFontId, 7);
    assert.ok(fs.existsSync(configPath));

    resetConfigCache();
    const reloaded = loadConfig();
    assert.equal(reloaded.defaultFontId, 7);
    assert.equal(reloaded.activityText, "Piano 24/7");
    assert.equal(reloaded.defaultEffectId, getEnvDefaults().defaultEffectId);
  });
});

test("ConfigStore: từ chối ghi khi dữ liệu không hợp lệ", async () => {
  await withTempConfig((configPath) => {
    const result = saveConfig({ maxFileSizeMb: 9999 });
    assert.equal(result.ok, false);
    assert.equal(result.errors.length, 1);
    assert.equal(fs.existsSync(configPath), false);
  });
});

test("ConfigStore: file JSON hỏng không làm sập bot", async () => {
  await withTempConfig((configPath) => {
    fs.mkdirSync(path.dirname(configPath), { recursive: true });
    fs.writeFileSync(configPath, "{ khong-phai-json");
    const config = loadConfig();
    assert.deepEqual(config, getEnvDefaults());
  });
});

test("WebPanel: safeCompare so sánh chính xác", () => {
  assert.equal(safeCompare("matkhau-bi-mat", "matkhau-bi-mat"), true);
  assert.equal(safeCompare("matkhau-bi-mat", "matkhau-bi-matx"), false);
  assert.equal(safeCompare("", "x"), false);
});

test("WebPanel: LoginThrottle chặn sau nhiều lần sai", () => {
  const throttle = new LoginThrottle({ maxFailures: 3, windowMs: 1000 });
  assert.equal(throttle.isBlocked("1.2.3.4"), false);

  throttle.recordFailure("1.2.3.4");
  throttle.recordFailure("1.2.3.4");
  assert.equal(throttle.isBlocked("1.2.3.4"), false);

  throttle.recordFailure("1.2.3.4");
  assert.equal(throttle.isBlocked("1.2.3.4"), true);
  assert.equal(throttle.isBlocked("5.6.7.8"), false);

  throttle.reset("1.2.3.4");
  assert.equal(throttle.isBlocked("1.2.3.4"), false);
});

test("WebPanel: SessionStore cấp và thu hồi phiên", () => {
  const store = new SessionStore({ ttlMs: 1000 });
  const { token } = store.create(0);

  assert.equal(store.isValid(token, 500), true);
  assert.equal(store.isValid(token, 1500), false);
  assert.equal(store.isValid("token-gia", 500), false);

  const second = store.create(0);
  store.destroy(second.token);
  assert.equal(store.isValid(second.token, 100), false);
});

async function startPanelServer() {
  const router = createPanelRouter({ client: null });
  const server = http.createServer(async (req, res) => {
    const url = new URL(req.url, "http://127.0.0.1");
    if (!(await router.handle(req, res, url))) {
      res.writeHead(404).end();
    }
  });

  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  return {
    base,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}

test("WebPanel: luồng đăng nhập và lưu cấu hình qua HTTP", async () => {
  const previousPassword = process.env.PANEL_PASSWORD;
  process.env.PANEL_PASSWORD = "mat-khau-kiem-thu-123";

  const server = await startPanelServer();
  try {
    await withTempConfig(async () => {
      const page = await fetch(`${server.base}/panel`);
      assert.equal(page.status, 200);
      assert.match(page.headers.get("content-type"), /text\/html/);
      assert.equal(page.headers.get("x-frame-options"), "DENY");

      const denied = await fetch(`${server.base}/api/panel/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: "sai-mat-khau" }),
      });
      assert.equal(denied.status, 401);

      const noAuth = await fetch(`${server.base}/api/panel/config`);
      assert.equal(noAuth.status, 401);

      const login = await fetch(`${server.base}/api/panel/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: "mat-khau-kiem-thu-123" }),
      });
      assert.equal(login.status, 200);
      const { token } = await login.json();
      assert.ok(token && token.length >= 32);

      const authHeaders = { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };

      const configResp = await fetch(`${server.base}/api/panel/config`, { headers: authHeaders });
      assert.equal(configResp.status, 200);
      const configPayload = await configResp.json();
      assert.equal(configPayload.meta.fonts.length, 12);
      assert.equal(configPayload.meta.effects.length, 6);
      assert.ok(!("password" in configPayload.config));

      const invalid = await fetch(`${server.base}/api/panel/config`, {
        method: "POST",
        headers: authHeaders,
        body: JSON.stringify({ defaultFontId: 42 }),
      });
      assert.equal(invalid.status, 400);

      const saved = await fetch(`${server.base}/api/panel/config`, {
        method: "POST",
        headers: authHeaders,
        body: JSON.stringify({ defaultFontId: 9, activityType: "Watching" }),
      });
      assert.equal(saved.status, 200);
      const savedPayload = await saved.json();
      assert.equal(savedPayload.config.defaultFontId, 9);
      assert.equal(savedPayload.config.activityType, "Watching");
      assert.equal(getConfig().defaultFontId, 9);

      const unknown = await fetch(`${server.base}/api/panel/khong-ton-tai`, { headers: authHeaders });
      assert.equal(unknown.status, 404);

      const loggedOut = await fetch(`${server.base}/api/panel/logout`, {
        method: "POST",
        headers: authHeaders,
      });
      assert.equal(loggedOut.status, 200);

      const afterLogout = await fetch(`${server.base}/api/panel/config`, { headers: authHeaders });
      assert.equal(afterLogout.status, 401);
    });
  } finally {
    await server.close();
    if (previousPassword === undefined) delete process.env.PANEL_PASSWORD;
    else process.env.PANEL_PASSWORD = previousPassword;
  }
});

test("WebPanel: bị khóa khi chưa đặt PANEL_PASSWORD", async () => {
  const previousPassword = process.env.PANEL_PASSWORD;
  delete process.env.PANEL_PASSWORD;

  const server = await startPanelServer();
  try {
    const response = await fetch(`${server.base}/panel`);
    assert.equal(response.status, 503);
    const payload = await response.json();
    assert.match(payload.error, /PANEL_PASSWORD/);
  } finally {
    await server.close();
    if (previousPassword !== undefined) process.env.PANEL_PASSWORD = previousPassword;
  }
});
