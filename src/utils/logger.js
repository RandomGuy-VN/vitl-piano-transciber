/**
 * Hệ thống ghi log đa màu sắc cho Node.js Discord Bot.
 */

const ANSI_COLORS = {
  reset: "\x1b[0m",
  cyan: "\x1b[36m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  red: "\x1b[31m",
  magenta: "\x1b[35m",
  gray: "\x1b[90m",
  bold: "\x1b[1m",
};

function getTimestamp() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ` +
         `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
}

export const logger = {
  info(msg, ...args) {
    const time = `${ANSI_COLORS.cyan}${getTimestamp()}${ANSI_COLORS.reset}`;
    const tag = `${ANSI_COLORS.green}[INFO]${ANSI_COLORS.reset}`;
    console.log(`${time} ${tag} ${msg}`, ...args);
  },
  warn(msg, ...args) {
    const time = `${ANSI_COLORS.cyan}${getTimestamp()}${ANSI_COLORS.reset}`;
    const tag = `${ANSI_COLORS.yellow}[WARN]${ANSI_COLORS.reset}`;
    console.warn(`${time} ${tag} ${msg}`, ...args);
  },
  error(msg, ...args) {
    const time = `${ANSI_COLORS.cyan}${getTimestamp()}${ANSI_COLORS.reset}`;
    const tag = `${ANSI_COLORS.red}[ERROR]${ANSI_COLORS.reset}`;
    console.error(`${time} ${tag} ${msg}`, ...args);
  },
  debug(msg, ...args) {
    if (process.env.DEBUG === "true") {
      const time = `${ANSI_COLORS.cyan}${getTimestamp()}${ANSI_COLORS.reset}`;
      const tag = `${ANSI_COLORS.magenta}[DEBUG]${ANSI_COLORS.reset}`;
      console.debug(`${time} ${tag} ${msg}`, ...args);
    }
  }
};
