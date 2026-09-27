# Vitl Piano Discord Bot — Base44 Dev Environment

## Architecture
Hybrid Node.js + Python app:
- **Node.js (discord.js v14)**: Discord bot, slash commands, web health server (port 3000 in Base44)
- **Python AI Core (aiohttp + PyTorch + Transkun)**: Audio-to-MIDI transcription (internal port 5000)
- `start.sh` launches both: Python AI Core first (background), then Node.js bot (foreground)

## Required Secret
- `DISCORD_BOT_TOKEN` — required at boot. Without it, the Node.js bot exits immediately and the health server dies.
  Get it from https://discord.com/developers/applications → Bot → Reset Token.

## Base44 Dev Setup
- `Dockerfile.base44` — installs system deps (ffmpeg, sox, Node.js 20), Python deps (torch CPU, transkun), and Node deps. Does NOT copy source.
- `docker-compose.base44.yml` — bind-mounts source at /app, anonymous volume preserves /app/node_modules, maps port 3000.
- Source edits are live (bind mount); restart the container for changes to take effect (no hot reload for a Discord bot).

## Key Config (set in compose environment)
- `PORT=3000` — health server on preview port
- `DEVICE=cpu` — no GPU in sandbox
- `PRELOAD_MODEL_ON_STARTUP=false` — skip model warmup for faster startup
- `ENABLE_AUTO_STYLE=false` — no Discord guilds to style in dev

## Health Check
- `GET /` — HTML dashboard
- `GET /health` — JSON status (bot, AI core, uptime, guilds)
- `GET /ping` — same as /health

## Build Notes
- torch CPU wheels (~200MB) make the first build slow (5-10 min)
- transkun includes pretrained model weights in the package
- The Python AI Core starts on 127.0.0.1:5000 (internal, same container)

## How to Verify
```bash
docker compose -f docker-compose.base44.yml up -d --build
docker compose -f docker-compose.base44.yml ps
curl -s http://localhost:3000/health | head -20
```
