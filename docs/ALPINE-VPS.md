# Triển khai Vitl Piano Bot trên Alpine Linux (Docker)

## ⚠️ Vì sao Alpine KHÔNG chạy native được

Bot cần **PyTorch** (qua `transkun`). PyTorch chỉ phát hành wheel biên dịch cho **glibc**
(`manylinux`, macOS, Windows) — **không có bản `musllinux`**. Alpine dùng **musl libc** thay
cho glibc, và kho Alpine cũng **không có gói `py3-torch`**.

Kiểm chứng (tra cứu thật):

| Kiểm tra | Kết quả |
|---|---|
| Wheel của `torch` trên PyPI có `musllinux`? | **0** (chỉ `manylinux1`, `manylinux2014`, `manylinux_2_28`, macOS, win) |
| `py3-torch` trong APKINDEX (edge/main + edge/community)? | **Không có** |
| `py3-torchaudio`, `py3-transkun`? | **Không có** |
| `ffmpeg`, `py3-numpy`? | Có |

→ `pip install torch` trên Alpine sẽ cố **biên dịch từ mã nguồn** (cần hàng giờ + toolchain C++),
và gần như chắc chắn thất bại. **Không có cách nào chạy native.**

**Cách duy nhất:** chạy trong container — image `python:3.12-slim-bookworm` (Debian, glibc)
đã có sẵn trong `Dockerfile` của dự án.

> Muốn chạy **native không Docker**? Phải dùng distro glibc: xem
> **[docs/UBUNTU-VPS.md](UBUNTU-VPS.md)** (Ubuntu/Debian + systemd).

---

## 1. Kiến trúc khi chạy trên Alpine

```
Alpine Linux (musl)
└── Docker daemon (OpenRC service)
    └── container vitl_piano_bot   ← image python:3.12-slim-bookworm (glibc)
        ├── Python AI Core  127.0.0.1:5000   (Transkun: audio → MIDI)
        └── Node.js Bot     (chỉ kết nối Discord, không mở cổng)
```

Cả hai tiến trình chạy trong **một container** qua `start.sh`.

---

## 2. Yêu cầu hệ thống

| Thành phần | Giá trị |
|---|---|
| Alpine Linux | 3.18+ (OpenRC) |
| Docker | cài tự động bởi script (`apk add docker`) |
| RAM | ≥ 4 GB (model Transkun chiếm ~1–2 GB khi nạp) |
| CPU | ≥ 2 vCPU |
| Ổ đĩa | ≥ 5 GB trống (image + PyTorch ~1.5 GB) |

---

## 3. Lấy mã nguồn

**Cách nhanh nhất — một dòng lệnh trên máy Alpine** (tự cài `git`/`curl`, clone vào
`/opt/vitl-piano-bot`, rồi chạy luôn `deploy/alpine/setup.sh`):

```sh
curl -fsSL https://raw.githubusercontent.com/RandomGuy-VN/vitl-piano-transciber/port-performance-optimization/deploy/alpine/bootstrap.sh | sudo sh
```

Lần đầu script dừng lại ở bước tạo `.env` để bạn điền token (xem mục 4), sau đó chạy lại
**đúng lệnh trên** — nó giữ nguyên `.env` và tiếp tục cài đặt.

> Đổi nhánh/thư mục: `curl ... | sudo VITL_BRANCH=main VITL_DIR=/opt/vitl-piano-bot sh`

**Cách thủ công (từ file zip):**

```sh
sudo mkdir -p /opt && cd /opt
unzip vitl-piano-bot-vps-v<version>.zip
cd vitl-piano-bot
```

> Đóng gói lại trên máy dev: `python3 scripts/build_release.py`
> → sinh ra `release/vitl-piano-bot-vps-v<version>.zip`.

---

## 4. Cấu hình `.env`

```sh
cd /opt/vitl-piano-bot
cp .env.example .env
vi .env            # điền DISCORD_BOT_TOKEN
```

| Biến | Giá trị | Ý nghĩa |
|---|---|---|
| `DISCORD_BOT_TOKEN` | *(bắt buộc)* | Token bot từ Discord Developer Portal → Bot → Reset Token |
| `GUILD_ID` | *(tùy chọn)* | ID server để slash command hiển thị ngay |
| `DEVICE` | `cpu` hoặc `auto` | VPS không GPU đặt `cpu` |
| `PRELOAD_MODEL_ON_STARTUP` | `false` | `false` = khởi động nhanh, model nạp ở request đầu tiên |
| `MAX_CONCURRENT_JOBS` | `1` | Giữ `1` nếu RAM < 4 GB |

> File `.env` được `docker compose` tự đọc và truyền vào container.

---

## 5. Cài đặt và chạy

```sh
sudo sh deploy/alpine/setup.sh
```

Script sẽ:

1. Cài `docker`, `docker-cli`, `docker-cli-compose`, `docker-cli-buildx` bằng `apk`.
2. Bật Docker daemon qua OpenRC (`rc-update add docker default` + `service docker start`).
3. Kiểm tra `.env` (tự tạo từ `.env.example` nếu chưa có và nhắc điền token).
4. `docker compose up -d --build`.
5. **Đợi AI Core trả lời `/health`** trong container rồi mới báo thành công; nếu lỗi thì in 60 dòng log cuối.

> **Về `/health`:** web health server của bot chỉ bật khi `BASE44_PREVIEW_MODE=1` (sandbox Base44),
> nên trên VPS **không có cổng HTTP nào**. Vì vậy script kiểm tra AI Core trực tiếp ở cổng 5000
> bên trong container.

---

## 6. Vận hành

```sh
# Trạng thái
sudo docker compose ps

# Xem log (Ctrl+C để thoát)
sudo docker compose logs -f

# Khởi động lại (sau khi sửa .env)
sudo docker compose restart

# Dừng / chạy
sudo docker compose down
sudo docker compose up -d

# Vào trong container để kiểm tra
sudo docker compose exec vitl-piano-bot sh
sudo docker compose exec vitl-piano-bot curl -s http://127.0.0.1:5000/health
```

Docker đã được bật tự khởi động cùng máy; container có `restart: unless-stopped` nên tự chạy lại.

---

## 7. Cập nhật phiên bản

```sh
cd /opt/vitl-piano-bot

# Thay mã nguồn mới (giải nén đè / git pull), GIỮ LẠI file .env
sudo docker compose down
sudo sh deploy/alpine/setup.sh
```

> Mỗi lần build lại image, model Transkun sẽ **tải lại weights** ở lần transcribe đầu tiên
> (vài trăm MB). Nếu rebuild thường xuyên, cân nhắc mount thêm cache model.

---

## 8. Tường lửa

Không cần mở cổng nào — container không phục vụ HTTP ra ngoài ở chế độ VPS
(cổng `8080` trong `docker-compose.yml` chỉ dùng cho web health server của sandbox).

---

## 9. Xử lý sự cố

| Triệu chứng | Nguyên nhân & cách xử lý |
|---|---|
| `pip install torch` báo lỗi / build từ source | Bạn đang chạy pip **trên host Alpine** (musl). Không làm vậy — phải chạy trong container qua `deploy/alpine/setup.sh` |
| `docker: command not found` | `sudo apk add docker docker-cli-compose` |
| `Cannot connect to the Docker daemon` | `sudo service docker start` (hoặc `sudo rc-service docker start`) |
| `docker compose` báo `unknown command` | Thiếu plugin → `sudo apk add docker-cli-compose` |
| Container `restarting` liên tục | `sudo docker compose logs --tail 80` — thường do token sai/rỗng |
| `Chưa tìm thấy Python AI Core tại cổng 5000` | AI Core chết trong container → xem `docker compose logs`; thường thiếu RAM (cần ≥ 4 GB) |
| Container bị OOM kill | Giảm `MAX_CONCURRENT_JOBS=1`, tăng RAM, hoặc thêm swap |
| Bot chạy nhưng `/transcript` rất chậm | Kiểm tra số vCPU, đặt `CPU_THREADS=0`, `MAX_CONCURRENT_JOBS=1` |
| Slash command không hiện | Đặt `GUILD_ID` để đồng bộ ngay, hoặc chờ vài phút với Global command |

---

## 10. Gỡ hoàn toàn

```sh
cd /opt/vitl-piano-bot
sudo docker compose down --rmi local
sudo apk del docker docker-cli docker-cli-compose docker-cli-buildx
```
