/**
 * Web Panel quản trị Bot: phục vụ giao diện tại /panel và REST API tại /api/panel/*.
 * Xác thực bằng mật khẩu PANEL_PASSWORD, phiên làm việc dùng Bearer token trong bộ nhớ.
 */

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { logger } from "../utils/logger.js";
import { AiClient } from "./aiClient.js";
import {
  ACTIVITY_TYPES,
  AI_CORE_FIELDS,
  DEVICE_CHOICES,
  getConfig,
  saveConfig,
} from "./configStore.js";
import {
  EFFECT_CHOICES,
  FONT_CHOICES,
  updateBotNameStyle,
} from "./styleService.js";

const PANEL_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "panel");

const MAX_BODY_BYTES = 64 * 1024;
const MAX_LOGIN_FAILURES = 8;
const LOGIN_WINDOW_MS = 10 * 60 * 1000;
const MAX_TRACKED_CLIENTS = 1000;

const STATIC_ROUTES = {
  "/panel": { file: "index.html", contentType: "text/html; charset=utf-8" },
  "/panel/": { file: "index.html", contentType: "text/html; charset=utf-8" },
  "/panel/app.js": { file: "app.js", contentType: "text/javascript; charset=utf-8" },
  "/panel/styles.css": { file: "styles.css", contentType: "text/css; charset=utf-8" },
};

const SECURITY_HEADERS = {
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
  "Referrer-Policy": "no-referrer",
  "Content-Security-Policy": "default-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
  "Cache-Control": "no-store",
};

function sessionTtlMs() {
  const minutes = parseInt(process.env.PANEL_SESSION_TTL_MINUTES || "480", 10);
  if (!Number.isFinite(minutes) || minutes < 5 || minutes > 10080) {
    return 480 * 60 * 1000;
  }
  return minutes * 60 * 1000;
}

/** So sánh chuỗi bí mật theo thời gian hằng số để chống timing attack. */
export function safeCompare(left, right) {
  const leftHash = crypto.createHash("sha256").update(String(left)).digest();
  const rightHash = crypto.createHash("sha256").update(String(right)).digest();
  return crypto.timingSafeEqual(leftHash, rightHash);
}

/** Bộ đếm số lần đăng nhập sai theo địa chỉ IP. */
export class LoginThrottle {
  constructor({ maxFailures = MAX_LOGIN_FAILURES, windowMs = LOGIN_WINDOW_MS } = {}) {
    this.maxFailures = maxFailures;
    this.windowMs = windowMs;
    this.clients = new Map();
  }

  isBlocked(clientId, now = Date.now()) {
    const entry = this.clients.get(clientId);
    if (!entry) return false;
    if (now >= entry.resetAt) {
      this.clients.delete(clientId);
      return false;
    }
    return entry.failures >= this.maxFailures;
  }

  recordFailure(clientId, now = Date.now()) {
    if (this.clients.size > MAX_TRACKED_CLIENTS) {
      for (const [key, entry] of this.clients) {
        if (now >= entry.resetAt) this.clients.delete(key);
      }
    }
    const entry = this.clients.get(clientId);
    if (!entry || now >= entry.resetAt) {
      this.clients.set(clientId, { failures: 1, resetAt: now + this.windowMs });
      return;
    }
    entry.failures += 1;
  }

  reset(clientId) {
    this.clients.delete(clientId);
  }
}

/** Quản lý phiên đăng nhập Panel trong bộ nhớ tiến trình. */
export class SessionStore {
  constructor({ ttlMs = sessionTtlMs() } = {}) {
    this.ttlMs = ttlMs;
    this.sessions = new Map();
  }

  create(now = Date.now()) {
    const token = crypto.randomBytes(32).toString("base64url");
    this.sessions.set(token, now + this.ttlMs);
    return { token, expiresAt: now + this.ttlMs };
  }

  isValid(token, now = Date.now()) {
    if (!token) return false;
    const expiresAt = this.sessions.get(token);
    if (!expiresAt) return false;
    if (now >= expiresAt) {
      this.sessions.delete(token);
      return false;
    }
    return true;
  }

  destroy(token) {
    this.sessions.delete(token);
  }

  prune(now = Date.now()) {
    for (const [token, expiresAt] of this.sessions) {
      if (now >= expiresAt) this.sessions.delete(token);
    }
  }
}

function sendJson(res, statusCode, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(statusCode, {
    ...SECURITY_HEADERS,
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(body),
  });
  res.end(body);
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;

    req.on("data", (chunk) => {
      size += chunk.length;
      if (size > MAX_BODY_BYTES) {
        reject(new Error("PAYLOAD_TOO_LARGE"));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });

    req.on("end", () => {
      if (chunks.length === 0) {
        resolve({});
        return;
      }
      try {
        const parsed = JSON.parse(Buffer.concat(chunks).toString("utf8"));
        resolve(parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {});
      } catch {
        reject(new Error("INVALID_JSON"));
      }
    });

    req.on("error", reject);
  });
}

function bearerToken(req) {
  const header = req.headers.authorization || "";
  return header.startsWith("Bearer ") ? header.slice(7).trim() : "";
}

function describeGuilds(client) {
  if (!client || !client.guilds || !client.guilds.cache) return [];
  return Array.from(client.guilds.cache.values()).map((guild) => ({
    id: guild.id,
    name: guild.name,
    memberCount: guild.memberCount ?? null,
  }));
}

/**
 * Tạo router xử lý toàn bộ request thuộc Web Panel.
 * `onConfigApplied` được gọi sau khi lưu cấu hình để áp dụng thay đổi lúc chạy.
 */
export function createPanelRouter({ client = null, onConfigApplied = null } = {}) {
  const enabled = (process.env.ENABLE_WEB_PANEL || "true").toLowerCase() === "true";
  const password = (process.env.PANEL_PASSWORD || "").trim();
  const sessions = new SessionStore();
  const throttle = new LoginThrottle();
  const staticCache = new Map();

  function loadStatic(fileName) {
    if (!staticCache.has(fileName)) {
      staticCache.set(fileName, fs.readFileSync(path.join(PANEL_DIR, fileName)));
    }
    return staticCache.get(fileName);
  }

  function serveStatic(res, route) {
    let body;
    try {
      body = loadStatic(route.file);
    } catch (err) {
      logger.error(`Không đọc được tài nguyên Web Panel '${route.file}':`, err.message);
      sendJson(res, 500, { error: "Không đọc được tài nguyên giao diện Panel." });
      return;
    }
    res.writeHead(200, {
      ...SECURITY_HEADERS,
      "Content-Type": route.contentType,
      "Content-Length": body.length,
    });
    res.end(body);
  }

  async function handleLogin(req, res, clientId) {
    if (throttle.isBlocked(clientId)) {
      sendJson(res, 429, { error: "Đăng nhập sai quá nhiều lần. Vui lòng thử lại sau 10 phút." });
      return;
    }

    let body;
    try {
      body = await readJsonBody(req);
    } catch (err) {
      const tooLarge = err.message === "PAYLOAD_TOO_LARGE";
      sendJson(res, tooLarge ? 413 : 400, {
        error: tooLarge ? "Dữ liệu gửi lên quá lớn." : "JSON không hợp lệ.",
      });
      return;
    }

    const submitted = typeof body.password === "string" ? body.password : "";
    if (!submitted || !safeCompare(submitted, password)) {
      throttle.recordFailure(clientId);
      logger.warn(`Đăng nhập Web Panel thất bại từ ${clientId}.`);
      sendJson(res, 401, { error: "Mật khẩu không đúng." });
      return;
    }

    throttle.reset(clientId);
    sessions.prune();
    const session = sessions.create();
    logger.info(`Đăng nhập Web Panel thành công từ ${clientId}.`);
    sendJson(res, 200, { token: session.token, expiresAt: session.expiresAt });
  }

  async function handleSaveConfig(req, res) {
    let body;
    try {
      body = await readJsonBody(req);
    } catch (err) {
      const tooLarge = err.message === "PAYLOAD_TOO_LARGE";
      sendJson(res, tooLarge ? 413 : 400, {
        error: tooLarge ? "Dữ liệu gửi lên quá lớn." : "JSON không hợp lệ.",
      });
      return;
    }

    const result = saveConfig(body);
    if (!result.ok) {
      sendJson(res, 400, { error: "Cấu hình không hợp lệ.", errors: result.errors });
      return;
    }

    let applied = [];
    if (typeof onConfigApplied === "function") {
      try {
        applied = (await onConfigApplied(result.config)) || [];
      } catch (err) {
        logger.warn("Không áp dụng được cấu hình mới lúc chạy:", err.message);
      }
    }

    sendJson(res, 200, {
      config: result.config,
      applied,
      restartRequiredFields: AI_CORE_FIELDS,
    });
  }

  async function handleApplyStyle(req, res) {
    let body;
    try {
      body = await readJsonBody(req);
    } catch (err) {
      const tooLarge = err.message === "PAYLOAD_TOO_LARGE";
      sendJson(res, tooLarge ? 413 : 400, {
        error: tooLarge ? "Dữ liệu gửi lên quá lớn." : "JSON không hợp lệ.",
      });
      return;
    }

    const config = getConfig();
    try {
      const result = await updateBotNameStyle({
        client,
        guildId: typeof body.guildId === "string" && body.guildId.trim() ? body.guildId.trim() : null,
        fontId: body.fontId ?? config.defaultFontId,
        effectId: body.effectId ?? config.defaultEffectId,
        hexColors: body.colors ?? config.defaultNameColors,
      });
      sendJson(res, 200, result);
    } catch (err) {
      logger.error("Lỗi khi áp dụng Style Tên Bot từ Web Panel:", err.message);
      sendJson(res, 502, { error: err.message });
    }
  }

  async function handleStatus(res) {
    const aiCore = await AiClient.checkHealth();
    const memory = process.memoryUsage();
    sendJson(res, 200, {
      bot: {
        online: Boolean(client && client.user),
        tag: client && client.user ? client.user.tag : null,
        id: client && client.user ? client.user.id : null,
        pingMs: client && client.ws ? client.ws.ping : null,
        uptimeSeconds: Math.floor(process.uptime()),
        guildsCount: client && client.guilds ? client.guilds.cache.size : 0,
        guilds: describeGuilds(client),
      },
      aiCore,
      system: {
        nodeVersion: process.version,
        platform: process.platform,
        memoryMb: Math.round((memory.rss / 1024 / 1024) * 100) / 100,
      },
    });
  }

  /**
   * Trả về true nếu request thuộc Web Panel và đã được xử lý.
   */
  async function handle(req, res, url) {
    const pathname = url.pathname;
    const isPanelRoute = pathname === "/panel" || pathname.startsWith("/panel/");
    const isApiRoute = pathname.startsWith("/api/panel/");
    if (!isPanelRoute && !isApiRoute) return false;

    if (!enabled) {
      sendJson(res, 404, { error: "Web Panel đang bị tắt (ENABLE_WEB_PANEL=false)." });
      return true;
    }

    if (!password) {
      sendJson(res, 503, {
        error: "Web Panel chưa được kích hoạt: hãy đặt biến môi trường PANEL_PASSWORD rồi khởi động lại bot.",
      });
      return true;
    }

    const clientId = req.socket.remoteAddress || "unknown";

    if (isPanelRoute) {
      const route = STATIC_ROUTES[pathname];
      if (!route || req.method !== "GET") {
        sendJson(res, 404, { error: "Không tìm thấy tài nguyên." });
        return true;
      }
      serveStatic(res, route);
      return true;
    }

    if (pathname === "/api/panel/login") {
      if (req.method !== "POST") {
        sendJson(res, 405, { error: "Phương thức không được hỗ trợ." });
        return true;
      }
      await handleLogin(req, res, clientId);
      return true;
    }

    const token = bearerToken(req);
    if (!sessions.isValid(token)) {
      sendJson(res, 401, { error: "Phiên đăng nhập không hợp lệ hoặc đã hết hạn." });
      return true;
    }

    switch (`${req.method} ${pathname}`) {
      case "POST /api/panel/logout":
        sessions.destroy(token);
        sendJson(res, 200, { ok: true });
        return true;

      case "GET /api/panel/status":
        await handleStatus(res);
        return true;

      case "GET /api/panel/config":
        sendJson(res, 200, {
          config: getConfig(),
          meta: {
            fonts: FONT_CHOICES,
            effects: EFFECT_CHOICES,
            activityTypes: ACTIVITY_TYPES,
            devices: DEVICE_CHOICES,
            aiCoreFields: AI_CORE_FIELDS,
          },
        });
        return true;

      case "POST /api/panel/config":
        await handleSaveConfig(req, res);
        return true;

      case "POST /api/panel/style/apply":
        await handleApplyStyle(req, res);
        return true;

      default:
        sendJson(res, 404, { error: "Không tìm thấy endpoint." });
        return true;
    }
  }

  return {
    handle,
    enabled,
    hasPassword: Boolean(password),
    sessions,
    throttle,
  };
}
