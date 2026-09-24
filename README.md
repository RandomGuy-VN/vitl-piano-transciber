# 🎹 Vitl Piano Discord Bot (Hybrid Architecture: Node.js + Python AI Core)

Discord Bot chuyên nghiệp sử dụng kiến trúc lai đa ngôn ngữ hiện đại:
- **Node.js (discord.js v14)**: Xử lý tương tác Discord Gateway, Slash Commands (`/transcript`, `/setstyle`), Web Health Server và tùy biến Display Name Styles.
- **Python 3.12 (PyTorch & Transkun AI)**: Lõi AI Microservice xử lý phân tích và chuyển đổi âm thanh sang tệp **MIDI (.mid)** chất lượng cao với khả năng tăng tốc phần cứng GPU NVIDIA CUDA.

Dự án đã được **tối ưu hóa toàn diện cho việc triển khai trên Cloud (Docker, Railway, Render, Fly.io, Koyeb, VPS, GPU Cloud)** và hỗ trợ chạy hoàn toàn tự động qua **GitHub Actions**.

---

## 🏛️ Kiến trúc hệ thống (System Architecture)

```text
┌─────────────────────────────────────────────────────────────┐
│                       DISCORD CLIENT                        │
│             (/transcript, /setstyle, Embeds)                │
└──────────────────────────────┬──────────────────────────────┘
                               │ Discord Gateway / REST v10
┌──────────────────────────────▼──────────────────────────────┐
│                  NODE.JS BOT (discord.js v14)               │
│  - Slash Commands Handler (/transcript, /setstyle)          │
│  - Web Health Check Server (Port 8080)                      │
│  - Display Name Styles (Font, Effect, Gradient)             │
│  - Web Panel cấu hình Bot (/panel, bảo vệ bằng mật khẩu)    │
└──────────────────────────────┬──────────────────────────────┘
                               │ Async HTTP REST (JSON / Multipart)
┌──────────────────────────────▼──────────────────────────────┐
│                 PYTHON AI CORE (Transkun Server)            │
│  - Audio Fetcher (pytubefix, scdl SoundCloud, Spotify)      │
│  - QueueManager (Semaphore chống OOM trên Cloud)            │
│  - Transkun Neural Network Inference (GPU CUDA / CPU)       │
│  - Memory Cleanup (gc.collect + torch.cuda.empty_cache)     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎨 Tính năng tùy biến Style Tên Bot (Display Name Styles)

Hỗ trợ tùy biến font chữ, hiệu ứng và dải màu (gradient) cho biệt danh hiển thị của Bot trên Discord:
- **Discord REST API v10 Endpoint**: `PATCH https://discord.com/api/v10/guilds/{guild_id}/members/@me`
- **12 kiểu Font chữ độc đáo**: Default, Gothic/Old English, Cursive, Bold Serif, Monospace, Double Struck, v.v.
- **6 kiểu Hiệu ứng (Effects)**: Standard, Neon Glow, Gradient Flow, Sparkle/Shimmer, Shadow Outline, Glitch/Pulse.
- **Dải màu Gradient (Lên tới 4 màu)**: Tự động chuyển đổi từ mã màu HEX (`#5865F2`, `#EB459E`, `#FEE75C`) sang số Decimal theo chuẩn Discord.
- **Slash Command `/setstyle`**: Cho phép Quản trị viên (Admin) hoặc Bot Owner thay đổi style trực tiếp qua Discord với phản hồi Ephemeral kèm bản xem trước trực quan.
- **Tự động áp dụng khi khởi động**: Thiết lập sẵn trong file `.env` hoặc GitHub Secrets để tự động chạy trong sự kiện `client.once("ready")`.

---

## 🚀 Khởi chạy dự án

### Cách 1: Chạy bằng script đồng thời (Khuyên dùng)
```bash
# 1. Cài đặt dependencies Python
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# 2. Cài đặt dependencies Node.js
npm install

# 3. Khởi chạy cả 2 dịch vụ
npm run start:all
# hoặc: ./start.sh
```

### Cách 2: Chạy độc lập từng dịch vụ (Development)
```bash
# Terminal 1: Chạy Python AI Core Server (Lắng nghe tại port 5000)
npm run ai-server
# hoặc: python3 ai_core/server.py

# Terminal 2: Chạy Node.js Discord Bot
npm start
# hoặc: node src/index.js
```

---

## 🖥️ Web Panel cấu hình Bot

Bot tích hợp sẵn bảng điều khiển web chạy chung cổng với Health Server (mặc định `8080`):

```text
http://<host>:8080/panel
```

### Kích hoạt

```bash
# Bắt buộc: đặt mật khẩu truy cập Panel (Panel bị khóa hoàn toàn nếu để trống)
PANEL_PASSWORD=<mật_khẩu_dài_ngẫu_nhiên>

# Tùy chọn
ENABLE_WEB_PANEL=true          # Đặt false để tắt hẳn Panel
PANEL_SESSION_TTL_MINUTES=480  # Thời hạn phiên đăng nhập
BOT_CONFIG_PATH=               # Mặc định: data/bot-config.json
```

### Tính năng

- **Theo dõi trạng thái trực tiếp**: tình trạng Bot, ping gateway, uptime, số server, tình trạng Python AI Core và mức sử dụng RAM.
- **Đổi Style tên Bot**: chọn font (1-12), hiệu ứng (1-6), dải màu gradient kèm xem trước và nút áp dụng ngay tới Discord API.
- **Tùy chỉnh Presence**: kiểu hoạt động (Playing / Listening / Watching / Competing) và nội dung hiển thị, áp dụng ngay không cần khởi động lại.
- **Điều chỉnh lõi AI & giới hạn**: thiết bị xử lý, số tác vụ song song, kích thước file, thời lượng audio, các mốc timeout.
- **Danh sách server** bot đang tham gia.

### Cơ chế lưu cấu hình

Panel ghi vào `data/bot-config.json`; file này ghi đè lên biến môi trường và được **cả Node.js Bot lẫn Python AI Core** đọc, nên cấu hình luôn đồng nhất giữa hai tiến trình. Thay đổi về Presence và Style có hiệu lực ngay; các mục thuộc lõi AI (thiết bị, số job song song, giới hạn tài nguyên) áp dụng sau khi khởi động lại AI Core.

### Bảo mật

- Đăng nhập bằng `PANEL_PASSWORD`, so sánh theo thời gian hằng số; Panel tự khóa nếu biến này trống.
- Phiên làm việc dùng Bearer token ngẫu nhiên 256-bit lưu trong bộ nhớ tiến trình (không dùng cookie nên không có rủi ro CSRF).
- Giới hạn 8 lần đăng nhập sai / 10 phút cho mỗi IP, giới hạn kích thước request 64 KB.
- Đặt sẵn `Content-Security-Policy`, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy: no-referrer`.
- Token Discord không bao giờ được gửi ra Panel. Khi mở Panel ra Internet, hãy đặt sau HTTPS (reverse proxy) hoặc chỉ truy cập qua mạng nội bộ.

---

## 🐙 Hướng dẫn chạy Bot qua GitHub Actions

Dự án tích hợp sẵn 2 Workflows chuẩn trong thư mục `.github/workflows/`:
1. **`run-bot.yml`**: Chạy trực tiếp Bot trên máy ảo GitHub Actions Runner (Miễn phí, tự động khởi động lại sau mỗi chu kỳ 5 tiếng).
2. **`docker-publish.yml`**: Tự động build và đẩy image Docker lên GitHub Container Registry (GHCR).

### Các bước thiết lập chạy Bot trên GitHub Actions:

#### Bước 1: Thêm Discord Token vào GitHub Secrets
1. Truy cập vào kho lưu trữ (Repository) của bạn trên GitHub.
2. Vào tab **Settings** -> **Secrets and variables** -> **Actions**.
3. Nhấn **New repository secret** và thêm các biến:
   - **Tên**: `DISCORD_BOT_TOKEN`
   - **Giá trị**: Điền Token Discord Bot của bạn.
4. *(Tùy chọn)* Thêm các secret khác nếu cần:
   - `GUILD_ID`: ID Server của bạn để đồng bộ slash commands ngay lập tức.
   - `DEFAULT_FONT_ID`: ID kiểu chữ mặc định (1-12).
   - `DEFAULT_EFFECT_ID`: ID hiệu ứng mặc định (1-6).
   - `DEFAULT_NAME_COLORS`: Dải màu mặc định (ví dụ: `#5865F2, #EB459E, #FEE75C`).

#### Bước 2: Kích hoạt chạy Bot
1. Vào tab **Actions** trên GitHub.
2. Tại cột bên trái, chọn workflow **Run Vitl Piano Discord Bot**.
3. Nhấn nút **Run workflow** -> Chọn nhánh `main` -> Nhấn nút xanh **Run workflow**.

---

## 📖 Hướng dẫn sử dụng Slash Commands

### 1. Lệnh `/transcript` (Chuyển đổi âm thanh sang MIDI)
- **Từ liên kết SoundCloud / YouTube / Spotify**:
  ```text
  /transcript url:https://soundcloud.com/artist/piano-track
  ```
  ```text
  /transcript url:https://www.youtube.com/watch?v=dQw4w9WgXcQ
  ```
  ```text
  /transcript url:https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT
  ```
- **Từ tệp âm thanh tải lên**:
  ```text
  /transcript file:[chọn file .mp3 / .wav / .m4a]
  ```

### 2. Lệnh `/setstyle` (Đổi Font chữ, Hiệu ứng & Gradient Tên Bot - Admin/Owner Only)
- **Cú pháp**:
  ```text
  /setstyle font_id:2 effect_id:3 colors:#5865F2, #EB459E, #FEE75C all_guilds:True
  ```
- **Tham số**:
  - `font_id` (1-12): Kiểu chữ mong muốn.
  - `effect_id` (1-6): Hiệu ứng mong muốn (Neon, Gradient, Sparkle, v.v.).
  - `colors`: Danh sách tối đa 4 mã màu HEX phân tách bằng dấu phẩy.
  - `all_guilds`: Áp dụng cho tất cả server hoặc chỉ server hiện tại.

---

## 🧪 Kiểm thử tự động (Unit & Integration Tests)

Chạy toàn bộ bộ test kiểm thử tự động của cả 2 ngôn ngữ:
```bash
# Chạy cả Node.js và Python tests
npm test

# Chạy riêng Node.js tests
node --test tests/node_tests.test.js

# Chạy riêng Python tests
python3 -m unittest discover tests
```
