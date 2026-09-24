/**
 * Kho cấu hình runtime cho Web Panel.
 * Giá trị mặc định lấy từ biến môi trường, sau đó được ghi đè bởi data/bot-config.json
 * để Panel có thể chỉnh sửa cấu hình mà không cần sửa file .env.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { logger } from "../utils/logger.js";

const PROJECT_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");

export const ACTIVITY_TYPES = ["Playing", "Listening", "Watching", "Competing"];
export const DEVICE_CHOICES = ["auto", "cpu", "cuda"];

/** Các trường chỉ có hiệu lực sau khi khởi động lại Python AI Core. */
export const AI_CORE_FIELDS = [
  "device",
  "maxConcurrentJobs",
  "preloadModelOnStartup",
  "maxFileSizeMb",
  "maxAudioDurationSeconds",
  "downloadTimeoutSeconds",
  "transcriptionTimeoutSeconds",
];

const HEX_COLOR_PATTERN = /^#?(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;

const FIELDS = {
  enableAutoStyle: { type: "boolean", env: "ENABLE_AUTO_STYLE", fallback: true },
  defaultFontId: { type: "int", env: "DEFAULT_FONT_ID", fallback: 1, min: 1, max: 12 },
  defaultEffectId: { type: "int", env: "DEFAULT_EFFECT_ID", fallback: 1, min: 1, max: 6 },
  defaultNameColors: { type: "colors", env: "DEFAULT_NAME_COLORS", fallback: "#5865F2, #EB459E, #FEE75C" },
  activityType: { type: "enum", env: "ACTIVITY_TYPE", fallback: "Listening", values: ACTIVITY_TYPES },
  activityText: { type: "text", env: "ACTIVITY_TEXT", fallback: "/transcript | Piano to MIDI", maxLength: 128 },
  device: { type: "enum", env: "DEVICE", fallback: "auto", values: DEVICE_CHOICES, lowercase: true },
  maxConcurrentJobs: { type: "int", env: "MAX_CONCURRENT_JOBS", fallback: 1, min: 1, max: 8 },
  preloadModelOnStartup: { type: "boolean", env: "PRELOAD_MODEL_ON_STARTUP", fallback: true },
  maxFileSizeMb: { type: "int", env: "MAX_FILE_SIZE_MB", fallback: 50, min: 1, max: 500 },
  maxAudioDurationSeconds: { type: "int", env: "MAX_AUDIO_DURATION_SECONDS", fallback: 900, min: 30, max: 7200 },
  downloadTimeoutSeconds: { type: "int", env: "DOWNLOAD_TIMEOUT_SECONDS", fallback: 180, min: 30, max: 1800 },
  transcriptionTimeoutSeconds: { type: "int", env: "TRANSCRIPTION_TIMEOUT_SECONDS", fallback: 600, min: 60, max: 3600 },
};

export const CONFIG_FIELD_NAMES = Object.keys(FIELDS);

export function getConfigPath() {
  const custom = (process.env.BOT_CONFIG_PATH || "").trim();
  return custom ? path.resolve(custom) : path.join(PROJECT_ROOT, "data", "bot-config.json");
}

function parseBoolean(value) {
  if (typeof value === "boolean") return value;
  const text = String(value).trim().toLowerCase();
  if (["true", "1", "yes", "on"].includes(text)) return true;
  if (["false", "0", "no", "off"].includes(text)) return false;
  return null;
}

function normalizeHexColors(value) {
  const items = Array.isArray(value)
    ? value.map((item) => String(item).trim())
    : String(value).split(/[,;\s]+/).map((item) => item.trim());

  const cleaned = items.filter(Boolean);
  if (cleaned.length === 0) {
    throw new Error("Cần ít nhất 1 mã màu HEX.");
  }
  if (cleaned.length > 4) {
    throw new Error("Chỉ hỗ trợ tối đa 4 mã màu HEX.");
  }

  return cleaned
    .map((item) => {
      if (!HEX_COLOR_PATTERN.test(item)) {
        throw new Error(`Mã màu HEX không hợp lệ: '${item}'.`);
      }
      let hex = item.replace(/^#/, "");
      if (hex.length === 3) {
        hex = hex.split("").map((char) => char + char).join("");
      }
      return `#${hex.toUpperCase()}`;
    })
    .join(", ");
}

function coerceField(name, spec, rawValue) {
  switch (spec.type) {
    case "boolean": {
      const parsed = parseBoolean(rawValue);
      if (parsed === null) throw new Error(`'${name}' phải là true hoặc false.`);
      return parsed;
    }
    case "int": {
      const parsed = Number(rawValue);
      if (!Number.isFinite(parsed) || !Number.isInteger(parsed)) {
        throw new Error(`'${name}' phải là số nguyên.`);
      }
      if (parsed < spec.min || parsed > spec.max) {
        throw new Error(`'${name}' phải nằm trong khoảng ${spec.min} - ${spec.max}.`);
      }
      return parsed;
    }
    case "enum": {
      const text = spec.lowercase ? String(rawValue).trim().toLowerCase() : String(rawValue).trim();
      if (!spec.values.includes(text)) {
        throw new Error(`'${name}' phải là một trong: ${spec.values.join(", ")}.`);
      }
      return text;
    }
    case "text": {
      const text = String(rawValue).trim();
      if (text.length > spec.maxLength) {
        throw new Error(`'${name}' tối đa ${spec.maxLength} ký tự.`);
      }
      return text;
    }
    case "colors":
      return normalizeHexColors(rawValue);
    default:
      throw new Error(`Kiểu dữ liệu không được hỗ trợ cho '${name}'.`);
  }
}

/**
 * Cấu hình mặc định đọc từ biến môi trường (các giá trị env sai định dạng sẽ bị bỏ qua).
 */
export function getEnvDefaults() {
  const defaults = {};
  for (const [name, spec] of Object.entries(FIELDS)) {
    const raw = (process.env[spec.env] || "").trim();
    if (!raw) {
      defaults[name] = spec.fallback;
      continue;
    }
    try {
      defaults[name] = coerceField(name, spec, raw);
    } catch {
      logger.warn(`Biến môi trường ${spec.env} không hợp lệ, dùng giá trị mặc định '${spec.fallback}'.`);
      defaults[name] = spec.fallback;
    }
  }
  return defaults;
}

/**
 * Kiểm tra và chuẩn hóa dữ liệu người dùng gửi lên, hợp nhất trên nền `base`.
 * Trả về { config, errors } — errors rỗng nghĩa là hợp lệ hoàn toàn.
 */
export function sanitizeConfig(input, base = getEnvDefaults()) {
  const config = { ...base };
  const errors = [];

  if (input === null || typeof input !== "object" || Array.isArray(input)) {
    return { config, errors: [{ field: "_", message: "Dữ liệu cấu hình phải là một object JSON." }] };
  }

  for (const [name, rawValue] of Object.entries(input)) {
    const spec = FIELDS[name];
    if (!spec) {
      errors.push({ field: name, message: `Trường '${name}' không được hỗ trợ.` });
      continue;
    }
    if (rawValue === null || rawValue === undefined || rawValue === "") {
      continue;
    }
    try {
      config[name] = coerceField(name, spec, rawValue);
    } catch (err) {
      errors.push({ field: name, message: err.message });
    }
  }

  return { config, errors };
}

let cachedConfig = null;

function readConfigFile() {
  const configPath = getConfigPath();
  let raw;
  try {
    raw = fs.readFileSync(configPath, "utf8");
  } catch {
    return {};
  }

  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
  } catch {
    logger.warn(`File cấu hình ${configPath} không phải JSON hợp lệ, bỏ qua và dùng biến môi trường.`);
    return {};
  }
}

/**
 * Nạp cấu hình từ file (ghi đè lên mặc định của env) và lưu vào bộ nhớ đệm.
 */
export function loadConfig() {
  const { config, errors } = sanitizeConfig(readConfigFile());
  for (const error of errors) {
    logger.warn(`Bỏ qua cấu hình không hợp lệ trong file: ${error.message}`);
  }
  cachedConfig = config;
  return { ...config };
}

export function getConfig() {
  if (!cachedConfig) {
    return loadConfig();
  }
  return { ...cachedConfig };
}

/**
 * Ghi cấu hình xuống đĩa theo kiểu atomic (ghi file tạm rồi rename).
 */
export function saveConfig(patch) {
  const { config, errors } = sanitizeConfig(patch, getConfig());
  if (errors.length > 0) {
    return { ok: false, errors, config: getConfig() };
  }

  const configPath = getConfigPath();
  const tempPath = `${configPath}.tmp`;
  fs.mkdirSync(path.dirname(configPath), { recursive: true });
  fs.writeFileSync(tempPath, `${JSON.stringify(config, null, 2)}\n`, { mode: 0o600 });
  fs.renameSync(tempPath, configPath);

  cachedConfig = config;
  logger.info(`Đã lưu cấu hình Bot vào ${configPath}`);
  return { ok: true, errors: [], config: { ...config } };
}

/** Xóa bộ nhớ đệm (dùng trong kiểm thử). */
export function resetConfigCache() {
  cachedConfig = null;
}
