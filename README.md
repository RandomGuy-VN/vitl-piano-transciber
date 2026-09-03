# 🎹 Vitl Piano Discord Bot (Cloud & GitHub Actions Ready)

Discord Bot chuyên nghiệp sử dụng công nghệ Deep Learning để chuyển đổi âm thanh piano (từ link YouTube, Spotify, SoundCloud hoặc file tải lên trực tiếp) thành tệp **MIDI (.mid)** chuẩn xác bằng mô hình **Transkun AI**.

Dự án đã được **tối ưu hóa toàn diện cho việc triển khai trên Cloud (Docker, Railway, Render, Fly.io, Koyeb, VPS, GPU Cloud)**, hỗ trợ chạy hoàn toàn tự động qua **GitHub Actions**, đồng thời tích hợp tính năng đổi font chữ, hiệu ứng neon/glow và dải màu gradient cho tên hiển thị của Bot qua Discord REST API v10.

---

## 🎨 Tính năng tùy biến Style Tên Bot (Display Name Styles)

Hỗ trợ tùy biến font chữ, hiệu ứng và dải màu (gradient) cho biệt danh hiển thị của Bot trên Discord:
- **Discord REST API v10 Endpoint**: `PATCH https://discord.com/api/v10/users/@me/guilds/{guild_id}/member`
- **12 kiểu Font chữ độc đáo**: Default, Gothic/Old English, Cursive, Bold Serif, Monospace, Double Struck, v.v.
- **6 kiểu Hiệu ứng (Effects)**: Standard, Neon Glow, Gradient Flow, Sparkle/Shimmer, Shadow Outline, Glitch/Pulse.
- **Dải màu Gradient (Lên tới 4 màu)**: Tự động chuyển đổi từ mã màu HEX (`#5865F2`, `#EB459E`, `#FEE75C`) sang số Decimal theo chuẩn Discord.
- **Slash Command `/setstyle`**: Cho phép Quản trị viên (Admin) hoặc Bot Owner thay đổi style trực tiếp qua Discord với phản hồi Ephemeral kèm bản xem trước trực quan.
- **Tự động áp dụng khi khởi động**: Thiết lập sẵn trong file `.env` hoặc GitHub Secrets để tự động chạy trong sự kiện `on_ready`.

---

## ☁️ Các tối ưu hóa chuyên biệt cho môi trường Cloud

1. 🌐 **Tích hợp Web Health Check HTTP Server (`PORT 8080`)**:
   - Cung cấp endpoint `GET /health`, `GET /status`, `GET /ping` và dashboard HTML giao diện tối hiện đại.
   - Giúp các nền tảng Cloud PaaS (Railway, Render, Fly.io, Kubernetes) duy trì bot luôn hoạt động (Keep-Alive) và không bị restart/shutdown do thiếu cổng web.
2. 🚦 **Hàng đợi thông minh & Kiểm soát tài nguyên (`QueueManager`)**:
   - Tích hợp cờ cấu hình `MAX_CONCURRENT_JOBS` (mặc định: 1 hoặc 2) bằng `asyncio.Semaphore`.
   - Khi có nhiều người dùng gửi lệnh cùng lúc, bot sẽ thông báo vị trí trong hàng đợi (Embed Cam) thay vì chạy đồng loạt làm sập bộ nhớ (tránh triệt để lỗi **OOM Kill** trên các gói Cloud 512MB - 4GB RAM).
3. 🚀 **Tự động làm nóng mô hình (`Model Warmup & Pre-loading`)**:
   - Tự động nạp trước weights của Transkun khi bot khởi động, loại bỏ hoàn toàn độ trễ (cold-start delay) cho người dùng đầu tiên.
4. 🧹 **Thu gom rác & Giải phóng bộ nhớ chủ động (`Garbage Collection`)**:
   - Tự động kích hoạt `gc.collect()` và `torch.cuda.empty_cache()` sau mỗi tiến trình chuyển đổi để giải phóng RAM/VRAM ngay lập tức.
5. 🛡️ **Container bảo mật**:
   - Dockerfile sử dụng `appuser` (non-root UID 10001) theo tiêu chuẩn bảo mật doanh nghiệp.

---

## 🐙 Hướng dẫn chạy Bot qua GitHub Actions

Dự án tích hợp sẵn 3 Workflows chuẩn trong thư mục `.github/workflows/`:
1. **`run-bot.yml`**: Chạy trực tiếp Bot trên máy ảo GitHub Actions Runner (Miễn phí, tự động khởi động lại sau mỗi chu kỳ 5 tiếng).
2. **`ci.yml`**: Tự động chạy bộ kiểm thử Unit & Integration Tests khi có push/pull request.
3. **`docker-publish.yml`**: Tự động build và đẩy image Docker lên GitHub Container Registry (GHCR).

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
4. Bot sẽ tự động khởi động, chạy bộ kiểm thử và kết nối vào Discord!
5. Workflow đã được cấu hình Cron `0 */5 * * *` để tự động xoay vòng và làm mới trước khi chạm mốc giới hạn 6 tiếng của GitHub Actions.

---

## 🚀 Hướng dẫn các cách triển khai lên Cloud khác

### 1. Triển khai lên Railway (Khuyên dùng nhất cho 24/7)
1. Đẩy mã nguồn lên kho GitHub của bạn.
2. Truy cập [railway.app](https://railway.app) -> Nhấn **New Project** -> Chọn **Deploy from GitHub repo**.
3. Chọn repository `vitl-piano-bot`.
4. Vào tab **Variables** và điền:
   - `DISCORD_BOT_TOKEN`: Token của Bot.
   - `DEVICE`: `auto` hoặc `cpu`.
   - `MAX_CONCURRENT_JOBS`: `1` (gói Starter) hoặc `2` (gói Pro).
5. Railway sẽ tự động build qua `Dockerfile` và gắn cổng Web Health Server hoàn toàn tự động.

### 2. Triển khai lên Render.com (Web Service)
1. Truy cập [render.com](https://render.com) -> **New +** -> **Web Service**.
2. Chọn repo GitHub của bot.
3. Chọn runtime **Docker**, Plan **Starter** (khuyến nghị từ 1GB RAM trở lên).
4. Đặt Health Check Path: `/health`.
5. Điền biến môi trường: `DISCORD_BOT_TOKEN` và nhấn **Deploy**.

### 3. Triển khai trên VPS cá nhân (Docker Compose)
```bash
git clone <repo_url> vitl-piano-bot
cd vitl-piano-bot
cp .env.example .env
nano .env # Điền DISCORD_BOT_TOKEN

# Chạy bot dưới nền
docker compose up -d --build
```

---

## 📖 Hướng dẫn sử dụng Slash Commands

### 1. Lệnh `/transcript` (Chuyển đổi âm thanh sang MIDI)
- **Từ liên kết YouTube / SoundCloud / Spotify**:
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

Chạy bộ test kiểm thử toàn diện:
```bash
python -m unittest discover tests
```
