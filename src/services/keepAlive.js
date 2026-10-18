/**
 * Keep-Alive Service — ping ngầm một URL mỗi 30 giây để giữ preview luôn tỉnh táo.
 */

import https from "node:https";
import http from "node:http";
import process from "node:process";
import { logger } from "../utils/logger.js";

const DEFAULT_INTERVAL_MS = 30_000;

let intervalId = null;

/**
 * Khởi động keep-alive, ping URL mỗi 30 giây.
 * @param {string} url - URL cần ping.
 * @param {number} [intervalMs=30000] - Khoảng thời gian giữa các lần ping (ms).
 */
export function startKeepAlive(url, intervalMs = DEFAULT_INTERVAL_MS) {
  if (!url) {
    logger.warn("Keep-Alive: không có URL để ping, bỏ qua.");
    return;
  }

  if (intervalId) {
    logger.warn("Keep-Alive: đã đang chạy, bỏ qua khởi động lại.");
    return;
  }

  const ping = () => {
    const lib = url.startsWith("https:") ? https : http;
    const req = lib.get(url, (res) => {
      // Đọc và giải phóng body để tránh rò rỉ socket
      res.resume();
      logger.info(`Keep-Alive: ping ${url} -> ${res.statusCode}`);
    });

    req.on("error", (err) => {
      logger.warn(`Keep-Alive: lỗi ping ${url} -> ${err.message}`);
    });
  };

  // Ping ngay lần đầu, sau đó lặp lại mỗi intervalMs
  ping();
  intervalId = setInterval(ping, intervalMs);

  logger.info(`Keep-Alive: đã khởi động — ping mỗi ${intervalMs / 1000}s tới ${url}`);
}

/**
 * Dừng keep-alive (dùng khi graceful shutdown).
 */
export function stopKeepAlive() {
  if (intervalId) {
    clearInterval(intervalId);
    intervalId = null;
    logger.info("Keep-Alive: đã dừng.");
  }
}
