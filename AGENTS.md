# Vitl Piano Bot — Base44 Dev Environment

## Architecture
- **Node.js Discord Bot** (`src/index.js`): Health HTTP server on port 3000, slash commands (`/transcript`, `/setstyle`, `/fonts`), style management with live-reload from web panel.
- **Python AI Core** (`ai_core/server.py`): Transkun AI transcription microservice on internal port 5000 (aiohttp).
- Both run in a **single container** via `scripts/start.dev.sh` — Python AI Core in background, Node.js bot in foreground with `node --watch`.

## Setup
```bash
docker compose -f docker-compose.base44.yml up -d --build
```
- Health: `curl http://localhost:3000/health`
- Dashboard: `http://localhost:3000/`

## Key Configuration
| Env | Default | Purpose |
|-----|---------|---------|
| `PORT` | 3000 | Web health server port (must be 3000 for preview) |
| `DEVICE` | cpu | No GPU in sandbox |
| `PRELOAD_MODEL_ON_STARTUP` | false | Faster startup; model loads on first transcription request |
| `DISCORD_BOT_TOKEN` | (secret) | Required — from `/run/base44/app.env` |
| `ENABLE_AUTO_STYLE` | true | Auto-apply bot display name style on startup |

## Live Reload
- Node.js bot uses `node --watch` — edits to `src/` auto-restart the bot within ~1s.
- Python AI Core has **no hot reload** — restart the container for AI Core changes: `docker compose -f docker-compose.base44.yml restart bot`.

## Performance Optimizations
- `PRELOAD_MODEL_ON_STARTUP=false` — skips loading the heavy Transkun model at boot (saves 10-30s).
- `DEVICE=cpu` — skips GPU/CUDA detection (no GPU in sandbox).
- `MAX_CONCURRENT_JOBS=1` — prevents OOM on limited resources.
- torch installed CPU-only (`--index-url https://download.pytorch.org/whl/cpu`) — smaller image, faster install.

## Verification
1. `docker compose -f docker-compose.base44.yml ps` — service should be `healthy`.
2. `curl http://localhost:3000/health` — returns JSON with bot status, guild count, ping, AI Core status.
3. Dashboard at `/` shows bot info in browser.
4. Check logs: `docker compose -f docker-compose.base44.yml logs bot`
