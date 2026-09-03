/**
 * Điểm khởi chạy chính (Entrypoint) cho Vitl Piano Discord Bot (Node.js).
 * Tích hợp discord.js v14, Web Health Server, Slash Commands và giao tiếp với Python AI Core.
 */

import http from "node:http";
import process from "node:process";
import {
  Client,
  GatewayIntentBits,
  REST,
  Routes,
  ActivityType,
  Collection,
} from "discord.js";
import dotenv from "dotenv";

import { logger } from "./utils/logger.js";
import { updateBotNameStyle } from "./services/styleService.js";
import { AiClient } from "./services/aiClient.js";
import * as transcriptCommand from "./commands/transcript.js";
import * as setstyleCommand from "./commands/setstyle.js";
import * as fontsCommand from "./commands/fonts.js";

// Nạp biến môi trường từ file .env
dotenv.config();

const TOKEN = (process.env.DISCORD_BOT_TOKEN || "").trim();
const GUILD_ID = (process.env.GUILD_ID || "").trim();
const PORT = parseInt(process.env.PORT || "8080", 10);
const ENABLE_HEALTH_SERVER = (process.env.ENABLE_HEALTH_SERVER || "true").toLowerCase() === "true";
const ENABLE_AUTO_STYLE = (process.env.ENABLE_AUTO_STYLE || "true").toLowerCase() === "true";

if (!TOKEN) {
  logger.error("LỖI: Chưa tìm thấy biến môi trường DISCORD_BOT_TOKEN!");
  process.exit(1);
}

// 1. Khởi tạo Discord Client
const client = new Client({
  intents: [GatewayIntentBits.Guilds],
});

client.commands = new Collection();
client.commands.set(transcriptCommand.data.name, transcriptCommand);
client.commands.set(setstyleCommand.data.name, setstyleCommand);
client.commands.set(fontsCommand.data.name, fontsCommand);

// 2. Web Health Check HTTP Server cho Cloud PaaS
let healthServer = null;
if (ENABLE_HEALTH_SERVER) {
  healthServer = http.createServer(async (req, res) => {
    const url = new URL(req.url, `http://${req.headers.host}`);
    if (url.pathname === "/health" || url.pathname === "/status" || url.pathname === "/ping") {
      const aiHealth = await AiClient.checkHealth();
      const payload = {
        status: "healthy",
        bot: client.user ? client.user.tag : "connecting",
        uptime_seconds: Math.floor(process.uptime()),
        guilds_count: client.guilds.cache.size,
        ping_ms: client.ws.ping,
        ai_core: aiHealth || { status: "offline", note: "Python AI Core not reachable on port 5000" },
      };
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify(payload, null, 2));
    } else {
      res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
      res.end(`
        <!DOCTYPE html>
        <html>
        <head><title>Vitl Piano Bot Dashboard</title></head>
        <body style="font-family: sans-serif; background: #0f172a; color: #f8fafc; padding: 2rem;">
          <h1>🎹 Vitl Piano Bot Dashboard (Node.js + Python AI)</h1>
          <p>Bot Status: <strong>ONLINE</strong> (Ping: ${client.ws.ping}ms)</p>
          <p>Guilds: <strong>${client.guilds.cache.size}</strong></p>
          <p><a href="/health" style="color: #38bdf8;">Xem chi tiết JSON Health</a></p>
        </body>
        </html>
      `);
    }
  });

  healthServer.listen(PORT, () => {
    logger.info(`Web Health Server đang lắng nghe trên cổng ${PORT}`);
  });
}

// 3. Đăng ký Slash Commands với Discord REST API
async function registerSlashCommands(clientId) {
  const rest = new REST({ version: "10" }).setToken(TOKEN);
  const commandsData = [
    transcriptCommand.data.toJSON(),
    setstyleCommand.data.toJSON(),
    fontsCommand.data.toJSON(),
  ];

  logger.info("Đang đồng bộ hóa Slash Commands với Discord API...");

  if (GUILD_ID) {
    try {
      await rest.put(Routes.applicationGuildCommands(clientId, GUILD_ID), {
        body: commandsData,
      });
      logger.info(`Đã đăng ký thành công ${commandsData.length} lệnh cho Guild ID: ${GUILD_ID}`);
      return;
    } catch (err) {
      logger.warn(`Không thể đồng bộ vào Guild ${GUILD_ID} (${err.message}). Tự động fallback về Global Commands...`);
    }
  }

  try {
    await rest.put(Routes.applicationCommands(clientId), {
      body: commandsData,
    });
    logger.info(`Đã đăng ký thành công ${commandsData.length} Slash Commands toàn cầu (Global)!`);
  } catch (err) {
    logger.error("Lỗi khi đăng ký Slash Commands toàn cầu:", err);
  }
}

// 4. Xử lý sự kiện Client Ready
client.once("ready", async () => {
  logger.info("=".repeat(60));
  logger.info("   🎹 VITL PIANO BOT (NODE.JS) ĐÃ SẴN SÀNG HOẠT ĐỘNG 🎹");
  logger.info("=".repeat(60));
  logger.info(`Tên Bot   : ${client.user.tag} (ID: ${client.user.id})`);
  logger.info(`Số Guilds : ${client.guilds.cache.size}`);

  client.guilds.cache.forEach((g) => {
    logger.info(` - Server: ${g.name} (ID: ${g.id})`);
  });

  // Đặt trạng thái hiện diện
  client.user.setActivity("/transcript | Piano to MIDI", {
    type: ActivityType.Listening,
  });

  // Đăng ký Slash Commands
  await registerSlashCommands(client.user.id);

  // Kiểm tra kết nối tới Python AI Core
  const aiStatus = await AiClient.checkHealth();
  if (aiStatus) {
    logger.info(`✅ Python AI Core kết nối thành công: ${aiStatus.device} (CUDA: ${aiStatus.is_cuda})`);
  } else {
    logger.warn("⚠️ Chưa tìm thấy Python AI Core tại cổng 5000. Hãy đảm bảo chạy 'npm run ai-server'!");
  }

  // Tự động áp dụng Style Tên Bot (Font, Effect, Gradient)
  if (ENABLE_AUTO_STYLE && client.guilds.cache.size > 0) {
    logger.info("Đang tự động áp dụng Style Tên Bot khi khởi động...");
    try {
      await new Promise((r) => setTimeout(r, 1000));
      const styleRes = await updateBotNameStyle({
        client,
        fontId: parseInt(process.env.DEFAULT_FONT_ID || "1", 10),
        effectId: parseInt(process.env.DEFAULT_EFFECT_ID || "1", 10),
        hexColors: process.env.DEFAULT_NAME_COLORS || "#5865F2, #EB459E, #FEE75C",
      });
      if (styleRes.success) {
        logger.info(`-> Tự động cập nhật Style Tên Bot thành công trên ${styleRes.updatedCount}/${styleRes.totalGuilds} servers!`);
      }
    } catch (styleErr) {
      logger.warn("Lỗi khi tự động cập nhật Style Tên Bot trong onReady:", styleErr.message);
    }
  }

  logger.info("=".repeat(60));
});

// 5. Xử lý sự kiện Interaction Create (Slash Commands)
client.on("interactionCreate", async (interaction) => {
  if (!interaction.isChatInputCommand()) return;

  const command = client.commands.get(interaction.commandName);
  if (!command) return;

  try {
    await command.execute(interaction);
  } catch (error) {
    logger.error(`Lỗi thực thi lệnh /${interaction.commandName}:`, error);
    if (interaction.replied || interaction.deferred) {
      await interaction.followUp({
        content: "❌ Đã có lỗi xảy ra khi thực hiện lệnh này.",
        ephemeral: true,
      });
    } else {
      await interaction.reply({
        content: "❌ Đã có lỗi xảy ra khi thực hiện lệnh này.",
        ephemeral: true,
      });
    }
  }
});

// 6. Graceful Shutdown
function handleShutdown(signal) {
  logger.info(`Nhận tín hiệu ${signal}. Đang tiến hành tắt Bot và giải phóng tài nguyên...`);
  if (healthServer) {
    healthServer.close();
  }
  client.destroy();
  process.exit(0);
}

process.on("SIGINT", () => handleShutdown("SIGINT"));
process.on("SIGTERM", () => handleShutdown("SIGTERM"));

// Khởi chạy Bot
client.login(TOKEN).catch((err) => {
  logger.error("Lỗi đăng nhập Discord Bot:", err);
  process.exit(1);
});
