/**
 * Logic phía trình duyệt cho Web Panel: đăng nhập, tải trạng thái và lưu cấu hình.
 * Token phiên được giữ trong sessionStorage và gửi qua header Authorization.
 */

const TOKEN_KEY = "vitl-panel-token";
const HEX_PATTERN = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;

const loginView = document.getElementById("login-view");
const appView = document.getElementById("app-view");
const loginForm = document.getElementById("login-form");
const loginError = document.getElementById("login-error");
const configForm = document.getElementById("config-form");
const colorsInput = document.getElementById("defaultNameColors");
const colorPreview = document.getElementById("color-preview");
const guildList = document.getElementById("guild-list");
const toastEl = document.getElementById("toast");

let toastTimer = null;
let configFields = [];

function getToken() {
  try {
    return sessionStorage.getItem(TOKEN_KEY) || "";
  } catch {
    return "";
  }
}

function setToken(token) {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // sessionStorage bị chặn: phiên chỉ tồn tại trong bộ nhớ trang hiện tại.
  }
}

function showToast(message, kind = "success") {
  toastEl.textContent = message;
  toastEl.className = `toast ${kind}`;
  toastEl.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toastEl.hidden = true;
  }, 6000);
}

function showLogin() {
  setToken("");
  appView.hidden = true;
  loginView.hidden = false;
}

async function api(path, { method = "GET", body = null } = {}) {
  const headers = { Authorization: `Bearer ${getToken()}` };
  if (body) headers["Content-Type"] = "application/json";

  const response = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  let payload = {};
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }

  if (response.status === 401) {
    showLogin();
    throw new Error(payload.error || "Phiên đăng nhập đã hết hạn.");
  }
  if (!response.ok) {
    const details = Array.isArray(payload.errors)
      ? payload.errors.map((item) => `• ${item.message}`).join("\n")
      : "";
    throw new Error([payload.error || `Lỗi HTTP ${response.status}`, details].filter(Boolean).join("\n"));
  }
  return payload;
}

function fillSelect(id, options) {
  const select = document.getElementById(id);
  select.replaceChildren();
  for (const option of options) {
    const element = document.createElement("option");
    element.value = String(option.value);
    element.textContent = option.name;
    select.append(element);
  }
}

function renderColorPreview() {
  const colors = colorsInput.value
    .split(/[,;\s]+/)
    .map((item) => item.trim())
    .filter((item) => HEX_PATTERN.test(item));

  if (colors.length === 0) {
    colorPreview.style.background = "transparent";
    return;
  }
  colorPreview.style.background =
    colors.length === 1 ? colors[0] : `linear-gradient(90deg, ${colors.join(", ")})`;
}

function applyConfigToForm(config) {
  for (const [name, value] of Object.entries(config)) {
    const input = document.getElementById(name);
    if (!input) continue;
    if (input.type === "checkbox") input.checked = Boolean(value);
    else input.value = String(value);
  }
  renderColorPreview();
}

function readFormValues() {
  const values = {};
  for (const name of configFields) {
    const input = document.getElementById(name);
    if (!input) continue;
    if (input.type === "checkbox") values[name] = input.checked;
    else if (input.type === "number") values[name] = Number(input.value);
    else values[name] = input.value;
  }
  return values;
}

function formatUptime(seconds) {
  const total = Math.max(0, Math.floor(seconds || 0));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  return hours > 0 ? `Uptime ${hours}h ${minutes}m` : `Uptime ${minutes}m`;
}

function renderGuilds(guilds) {
  guildList.replaceChildren();
  if (!guilds || guilds.length === 0) {
    const empty = document.createElement("li");
    empty.className = "muted";
    empty.textContent = "Bot chưa tham gia server nào.";
    guildList.append(empty);
    return;
  }

  for (const guild of guilds) {
    const item = document.createElement("li");
    const name = document.createElement("span");
    name.textContent = guild.memberCount
      ? `${guild.name} · ${guild.memberCount} thành viên`
      : guild.name;
    const id = document.createElement("span");
    id.className = "guild-id";
    id.textContent = guild.id;
    item.append(name, id);
    guildList.append(item);
  }
}

async function loadStatus() {
  const data = await api("/api/panel/status");
  const { bot, aiCore, system } = data;

  document.getElementById("bot-identity").textContent = bot.tag
    ? `${bot.tag} · ID ${bot.id}`
    : "Bot chưa kết nối tới Discord";
  document.getElementById("stat-bot").textContent = bot.online ? "Online" : "Đang kết nối";
  document.getElementById("stat-ping").textContent =
    bot.pingMs === null || bot.pingMs < 0 ? "" : `Ping ${Math.round(bot.pingMs)}ms`;
  document.getElementById("stat-guilds").textContent = String(bot.guildsCount);
  document.getElementById("stat-uptime").textContent = formatUptime(bot.uptimeSeconds);
  document.getElementById("stat-ai").textContent = aiCore ? "Online" : "Offline";
  document.getElementById("stat-ai-note").textContent = aiCore
    ? `${aiCore.device} · ${aiCore.active_jobs}/${aiCore.max_concurrent_jobs} job`
    : "Không kết nối được cổng 5000";
  document.getElementById("stat-memory").textContent = `${system.memoryMb} MB`;
  document.getElementById("stat-node").textContent = `Node ${system.nodeVersion}`;

  renderGuilds(bot.guilds);
}

async function loadConfig() {
  const { config, meta } = await api("/api/panel/config");
  configFields = Object.keys(config);

  fillSelect("defaultFontId", meta.fonts);
  fillSelect("defaultEffectId", meta.effects);
  fillSelect(
    "activityType",
    meta.activityTypes.map((value) => ({ name: value, value }))
  );
  fillSelect(
    "device",
    meta.devices.map((value) => ({ name: value.toUpperCase(), value }))
  );

  applyConfigToForm(config);
}

async function enterPanel() {
  loginView.hidden = true;
  appView.hidden = false;
  try {
    await loadConfig();
    await loadStatus();
  } catch (err) {
    showToast(err.message, "error");
  }
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginError.hidden = true;
  const button = loginForm.querySelector("button");
  button.disabled = true;

  try {
    const response = await fetch("/api/panel/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: document.getElementById("login-password").value }),
    });
    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      loginError.textContent = payload.error || `Lỗi HTTP ${response.status}`;
      loginError.hidden = false;
      return;
    }

    setToken(payload.token);
    document.getElementById("login-password").value = "";
    await enterPanel();
  } catch (err) {
    loginError.textContent = err.message;
    loginError.hidden = false;
  } finally {
    button.disabled = false;
  }
});

configForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = configForm.querySelector("button[type=submit]");
  button.disabled = true;

  try {
    const result = await api("/api/panel/config", { method: "POST", body: readFormValues() });
    applyConfigToForm(result.config);
    showToast("Đã lưu cấu hình. Các mục thuộc AI Core cần khởi động lại để có hiệu lực.", "success");
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    button.disabled = false;
  }
});

document.getElementById("apply-style-btn").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  button.disabled = true;

  try {
    const result = await api("/api/panel/style/apply", {
      method: "POST",
      body: {
        fontId: Number(document.getElementById("defaultFontId").value),
        effectId: Number(document.getElementById("defaultEffectId").value),
        colors: colorsInput.value,
      },
    });
    showToast(
      result.success
        ? `Đã áp dụng style cho ${result.updatedCount}/${result.totalGuilds} server.`
        : `Không áp dụng được style: ${result.details || `${result.failedCount} server thất bại`}`,
      result.success ? "success" : "error"
    );
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    button.disabled = false;
  }
});

document.getElementById("refresh-btn").addEventListener("click", async () => {
  try {
    await loadStatus();
    showToast("Đã làm mới trạng thái.", "success");
  } catch (err) {
    showToast(err.message, "error");
  }
});

document.getElementById("logout-btn").addEventListener("click", async () => {
  try {
    await api("/api/panel/logout", { method: "POST" });
  } catch {
    // Phiên có thể đã hết hạn sẵn, vẫn quay về màn đăng nhập.
  }
  showLogin();
});

colorsInput.addEventListener("input", renderColorPreview);

if (getToken()) {
  enterPanel();
}
