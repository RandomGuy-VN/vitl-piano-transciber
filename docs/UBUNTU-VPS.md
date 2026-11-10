# Triển khai Vitl Piano Bot trên Ubuntu Server (native — không Docker)

Hướng dẫn chạy Bot trực tiếp trên VPS Ubuntu bằng Python + Node.js (không Docker) và
đăng ký thành **systemd service** để tự khởi động cùng máy và tự chạy lại khi lỗi.

---

## 1. Kiến trúc khi chạy trên VPS

| Tiến trình | Tệp | Cổng | Vai trò |
|---|---|---|---|
| **Python AI Core** | `ai_core/server.py` | `127.0.0.1:5000` (nội bộ) | Chạy model Transkun: audio → MIDI |
| **Node.js Discord Bot** | `src/index.js` | *không mở cổng* | Nhận slash commands, gọi AI Core qua HTTP nội bộ |

> Cả hai chỉ lắng nghe trên `127.0.0.1` → **không cần mở cổng nào** trên tường lửa.

---

## 2. Yêu cầu hệ thống

| Thành phần | Phiên bản | Ghi chú |
|---|---|---|
| Ubuntu Server | 22.04 / 24.04 | 24.04 có sẵn `python3.12` |
| **Python** | **3.12.x** | 22.04 cần thêm PPA deadsnakes |
| **Node.js** | **20 LTS** | Cài qua NodeSource (có `/usr/bin/node`) |
| **FFmpeg** | 6.0+ | Cần cả `ffmpeg` **và** `ffprobe` |
| RAM | ≥ 4 GB | Model Transkun chiếm ~1–2 GB khi đã nạp |
| CPU | ≥ 2 vCPU | Càng nhiều nhân, transcription càng nhanh |

---

## 3. Cài phần mềm nền

```bash
sudo apt update
sudo apt install -y curl unzip ffmpeg python3-venv

# Python 3.12 — Ubuntu 24.04 đã có sẵn, chỉ Ubuntu 22.04 mới cần PPA
sudo add-apt-repository -y ppa:deadsnakes/ppa   # chỉ chạy trên Ubuntu 22.04
sudo apt install -y python3.12 python3.12-venv

# Node.js 20 LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

Kiểm tra:

```bash
python3.12 --version      # Python 3.12.x
node --version            # v20.x
ffmpeg -version  | head -1
ffprobe -version | head -1
```

---

## 4. Lấy mã nguồn

```bash
sudo mkdir -p /opt && sudo chown "$USER":"$USER" /opt
cd /opt
unzip vitl-piano-bot-vps-v<version>.zip
cd vitl-piano-bot
```

> Đóng gói lại file phát hành trên máy dev: `python3 scripts/build_release.py`
> → sinh ra `release/vitl-piano-bot-vps-v<version>.zip`.
> Hoặc dùng `git clone` nếu bạn muốn nhận cập nhật qua git.

---

## 5. Cấu hình `.env`

```bash
cd /opt/vitl-piano-bot
cp .env.example .env
nano .env        # điền DISCORD_BOT_TOKEN
```

| Biến | Giá trị | Ý nghĩa |
|---|---|---|
| `DISCORD_BOT_TOKEN` | *(bắt buộc)* | Token bot từ Discord Developer Portal → Bot → Reset Token |
| `GUILD_ID` | *(tùy chọn)* | ID server để slash command hiển thị ngay (bỏ trống = Global, chờ 1–15 phút) |
| `DEVICE` | `cpu` hoặc `auto` | `auto` tự dùng GPU nếu có; VPS không GPU đặt `cpu` |
| `PRELOAD_MODEL_ON_STARTUP` | `false` | `false` = khởi động nhanh, model nạp ở request đầu tiên |
| `MAX_CONCURRENT_JOBS` | `1` | Giữ `1` nếu RAM < 4 GB để tránh OOM |
| `CPU_THREADS` | `0` | `0` = tự động theo số vCPU |

---

## 6. Cài dependencies

```bash
cd /opt/vitl-piano-bot
bash deploy/ubuntu/setup.sh            # PyTorch bản CPU
# bash deploy/ubuntu/setup.sh --cuda   # nếu VPS có GPU NVIDIA
```

> **Không cần `sudo`** cho bước này — mọi thứ được cài trong `.venv` và `node_modules` của dự án.

Script sẽ: tạo `.venv`, cài PyTorch + `requirements.txt`, chạy `npm ci`, và tạo `.env` nếu chưa có.

---

## 7. Chạy thử trước khi cài service

```bash
bash deploy/ubuntu/run-manual.sh
```

Kết quả mong đợi:

- `==> AI Core da san sang.` (log chi tiết ở `logs/ai_core.log`)
- Bot báo `🎹 VITL PIANO BOT (NODE.JS) ĐÃ SẴN SÀNG HOẠT ĐỘNG 🎹`
  và `✅ Python AI Core kết nối thành công: CPU (CUDA: false)`

Thử gõ `/transcript` trong Discord để chắc chắn bot trả về file MIDI.
Nhấn `Ctrl+C` để dừng cả bot và AI Core.

> Nếu AI Core không khởi động được, script **in 30 dòng log cuối rồi dừng lại** (không chạy bot
> trong tình trạng hỏng). Muốn xem lỗi trực tiếp, chạy nền trước:
> `.venv/bin/python ai_core/server.py`

---

## 8. Cài đặt thành systemd service

```bash
sudo bash deploy/ubuntu/install-services.sh
```

Script tạo 2 service:

| Service | Chạy | Tự khởi động | Phụ thuộc |
|---|---|---|---|
| `vitl-piano-ai` | `.venv/bin/python ai_core/server.py` | ✔ | — |
| `vitl-piano-bot` | `node src/index.js` | ✔ | `vitl-piano-ai` |

- Service chạy bằng **user thường gọi `sudo`** (không chạy bot bằng root).
- Script **đợi AI Core trả lời `/health`** rồi mới start Bot, và in log lỗi nếu AI Core không lên.

Lệnh quản lý:

```bash
systemctl status vitl-piano-ai vitl-piano-bot
sudo systemctl restart vitl-piano-bot     # sau khi sửa .env hoặc mã Node.js
sudo systemctl restart vitl-piano-ai      # sau khi sửa mã Python
sudo systemctl stop vitl-piano-bot vitl-piano-ai
```

Gỡ service (giữ nguyên mã nguồn + `.venv` + log):

```bash
sudo bash deploy/ubuntu/uninstall-services.sh
```

---

## 9. Vận hành & bảo trì

| Tệp | Nội dung |
|---|---|
| `logs/bot.log` | Nhật ký Node.js Bot |
| `logs/bot.error.log` | Lỗi của Node.js Bot |
| `logs/ai_core.log` | Nhật ký Python AI Core |
| `logs/ai_core.error.log` | Lỗi của Python AI Core |

```bash
# Theo dõi log trực tiếp
tail -f logs/bot.log
journalctl -u vitl-piano-bot -f

# Xem 100 dòng gần nhất
journalctl -u vitl-piano-ai -n 100 --no-pager
```

> Bot không có web dashboard khi chạy trên VPS — trạng thái xem qua log và Discord.

---

## 10. Cập nhật phiên bản

```bash
sudo systemctl stop vitl-piano-bot vitl-piano-ai

# Thay mã nguồn mới (giải nén đè hoặc git pull), giữ nguyên file .env
bash deploy/ubuntu/setup.sh

sudo systemctl start vitl-piano-ai
sudo systemctl start vitl-piano-bot
```

Nếu chỉ sửa `.env`: `sudo systemctl restart vitl-piano-bot` là đủ.

---

## 11. Tường lửa

Không cần mở cổng nào (AI Core chỉ nghe trên loopback):

```bash
sudo ufw allow OpenSSH
sudo ufw enable
sudo ufw status
```

---

## 12. Xử lý sự cố

| Triệu chứng | Nguyên nhân & cách xử lý |
|---|---|
| `Chưa tìm thấy Python AI Core tại cổng 5000` / `connect ECONNREFUSED 127.0.0.1:5000` | AI Core chưa chạy được. Xem `logs/ai_core.error.log`; hoặc chạy nền trước để thấy lỗi ngay: `.venv/bin/python ai_core/server.py` |
| `ModuleNotFoundError` khi chạy AI Core | Thiếu gói → chạy lại `bash deploy/ubuntu/setup.sh` |
| `python3 -m venv` báo thiếu `ensurepip` | Thiếu gói venv → `sudo apt install -y python3-venv python3.12-venv` |
| `ffprobe: not found` / lỗi đo thời lượng | FFmpeg chưa cài → `sudo apt install -y ffmpeg` |
| Service `vitl-piano-bot` dừng ngay sau khi start | Sai đường dẫn `node` (thường do cài bằng nvm) → cài lại Node 20 qua NodeSource rồi chạy lại `install-services.sh` |
| Service báo `status=203/EXEC` | Không có quyền đọc `ExecStart` (thư mục dự án nằm trong `/root` hoặc chưa `chown`) → `sudo chown -R "$USER":"$USER" /opt/vitl-piano-bot` |
| Lỗi `torch` / CUDA không khả dụng | Cài sai bản PyTorch → chạy lại `setup.sh` (CPU) hoặc `setup.sh --cuda` (GPU) |
| Bot chạy nhưng `/transcript` rất chậm | Kiểm tra số vCPU, đặt `CPU_THREADS=0` (tự động) và `MAX_CONCURRENT_JOBS=1` |
| Slash command không hiện | Đặt `GUILD_ID` để đồng bộ ngay, hoặc chờ vài phút với Global command |
