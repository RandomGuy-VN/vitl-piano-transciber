# Triển khai Vitl Piano Bot trên Windows Server 2025 (native — không Docker)

Hướng dẫn này cài bot chạy trực tiếp trên Windows Server 2025 bằng **Python 3.12 + Node.js 20**,
và đăng ký thành **Windows Service** để tự khởi động cùng máy và tự chạy lại khi gặp lỗi.

> **Không cần mở bất kỳ cổng nào ra Internet** và không cần IIS. Bot chỉ kết nối *ra ngoài*
> tới Discord; Python AI Core chỉ lắng nghe nội bộ tại `127.0.0.1:5000`.

---

## 1. Kiến trúc khi chạy trên VPS

| Tiến trình | Tệp | Cổng | Vai trò |
|---|---|---|---|
| **Python AI Core** | `ai_core/server.py` | `127.0.0.1:5000` (nội bộ) | Chạy model Transkun: audio → MIDI |
| **Node.js Discord Bot** | `src/index.js` | *không mở cổng* | Nhận slash commands, gọi AI Core qua HTTP nội bộ |

Bot Node.js giao tiếp với AI Core qua biến môi trường `AI_CORE_URL` (mặc định `http://127.0.0.1:5000`).

---

## 2. Yêu cầu hệ thống

| Thành phần | Phiên bản | Ghi chú |
|---|---|---|
| Windows Server 2025 | — | Bất kỳ edition nào |
| **Python** | **3.12.x** | Khi cài **BẮT BUỘC** tick *"Add python.exe to PATH"* |
| **Node.js** | **20 LTS** | Bản Windows Installer (.msi) |
| **FFmpeg** | 6.0+ | Cần cả `ffmpeg` **và** `ffprobe` trong PATH |
| **NSSM** | 2.24+ | Để chạy như Windows Service |
| RAM | ≥ 4 GB | Model Transkun chiếm ~1–2 GB khi đã nạp |
| CPU | ≥ 2 vCPU | Càng nhiều nhân, transcription càng nhanh |

---

## 3. Cài phần mềm nền

Mở **PowerShell với quyền Administrator**.

### 3.1. Cài bằng winget (nếu có)

```powershell
winget install --id Python.Python.3.12 -e
winget install --id OpenJS.NodeJS.LTS -e
winget install --id Gyan.FFmpeg -e
```

> Windows Server thường **không có sẵn winget**. Nếu lệnh trên báo không tìm thấy `winget`,
> hãy cài thủ công theo mục 3.2.

### 3.2. Cài thủ công

1. **Python 3.12** — https://www.python.org/downloads/windows/ → *Windows installer (64-bit)*.
   Khi cài nhớ tick **"Add python.exe to PATH"**.
2. **Node.js 20 LTS** — https://nodejs.org/en/download → *Windows Installer (.msi)*.
3. **FFmpeg** — https://www.gyan.dev/ffmpeg/builds/ → tải bản `ffmpeg-release-essentials`.
   Giải nén (ví dụ `C:\ffmpeg`), rồi thêm `C:\ffmpeg\bin` vào **PATH** hệ thống.
4. **NSSM** — https://nssm.cc/download → giải nén, thêm thư mục `win64` vào **PATH**
   (hoặc nhớ đường dẫn `nssm.exe` để truyền bằng tham số `-NssmPath`).

### 3.3. Kiểm tra

Đóng và mở lại PowerShell (để nạp PATH mới), rồi chạy:

```powershell
python --version     # Python 3.12.x
node --version       # v20.x
ffmpeg -version
ffprobe -version
nssm version
```

---

## 4. Lấy mã nguồn

Giải nén gói `vitl-piano-bot-vps-v*.zip` vào một thư mục, ví dụ:

```text
C:\VitlPianoBot\
```

Sau khi giải nén, thư mục này chính là thư mục gốc dự án (chứa `package.json`, `requirements.txt`, `src\`, `ai_core\`).

---

## 5. Cấu hình `.env`

Sao chép `.env.example` thành `.env` rồi mở bằng Notepad:

```powershell
cd C:\VitlPianoBot
Copy-Item .env.example .env
notepad .env
```

Điền tối thiểu:

| Biến | Giá trị | Ý nghĩa |
|---|---|---|
| `DISCORD_BOT_TOKEN` | *(bắt buộc)* | Token bot lấy từ Discord Developer Portal → Bot → Reset Token |
| `GUILD_ID` | *(tùy chọn)* | ID server để slash command hiển thị ngay (bỏ trống = Global, chờ 1–15 phút) |
| `DEVICE` | `cpu` hoặc `auto` | `auto` sẽ tự dùng GPU nếu có; VPS không GPU đặt `cpu` |
| `PRELOAD_MODEL_ON_STARTUP` | `false` | `false` = khởi động nhanh, model nạp ở request đầu tiên |
| `MAX_CONCURRENT_JOBS` | `1` | Giữ `1` nếu RAM < 4 GB để tránh OOM |

---

## 6. Cài dependencies

```powershell
cd C:\VitlPianoBot
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\deploy\windows\setup.ps1
```

Script sẽ: tạo virtualenv `.venv`, cài PyTorch (bản CPU) + `requirements.txt`, chạy `npm ci`, và tạo `.env` nếu chưa có.

> **Có GPU NVIDIA?** Chạy `.\deploy\windows\setup.ps1 -Cuda` để cài PyTorch bản CUDA.

---

## 7. Chạy thử trước khi cài service

```powershell
.\deploy\windows\run-manual.ps1
```

Kết quả mong đợi:

- Cửa sổ AI Core báo `AI Core Service đã sẵn sàng lắng nghe tại http://127.0.0.1:5000`
- Cửa sổ bot báo `🎹 VITL PIANO BOT (NODE.JS) ĐÃ SẴN SÀNG HOẠT ĐỘNG 🎹`
  và `✅ Python AI Core kết nối thành công: CPU (CUDA: false)`

Thử gõ `/transcript` trong Discord để chắc chắn bot trả về file MIDI.
Nhấn `Ctrl+C` để dừng bot, đóng cửa sổ AI Core để dừng AI Core.

---

## 8. Cài đặt thành Windows Service

```powershell
.\deploy\windows\install-services.ps1
```

Script tạo 2 service (dùng NSSM):

| Service | Chạy | Tự khởi động | Phụ thuộc |
|---|---|---|---|
| `VitlPianoAI` | `python ai_core\server.py` | ✔ | — |
| `VitlPianoBot` | `node src\index.js` | ✔ | `VitlPianoAI` |

Nếu `nssm.exe` không nằm trong PATH:

```powershell
.\deploy\windows\install-services.ps1 -NssmPath "C:\nssm\win64\nssm.exe"
```

Kiểm tra:

```powershell
Get-Service VitlPianoAI, VitlPianoBot
Get-Content .\logs\bot.log -Tail 30 -Wait
```

---

## 9. Vận hành & bảo trì

```powershell
# Xem trạng thái
Get-Service VitlPianoAI, VitlPianoBot

# Khởi động lại bot (sau khi sửa .env)
nssm restart VitlPianoBot

# Dừng / chạy
nssm stop VitlPianoBot
nssm start VitlPianoBot
```

**Nhật ký (log):**

| Tệp | Nội dung |
|---|---|
| `logs\bot.log` | Nhật ký Node.js Bot |
| `logs\bot.error.log` | Lỗi của Node.js Bot |
| `logs\ai_core.log` | Nhật ký Python AI Core |
| `logs\ai_core.error.log` | Lỗi của Python AI Core |

NSSM tự xoay vòng log khi vượt 10 MB.

**Cập nhật phiên bản mới:**

1. Giải nén gói mới, chép đè các tệp mã nguồn (giữ nguyên `.env`, `.venv`, `node_modules`, `data\`).
2. Nếu `requirements.txt` hoặc `package.json` thay đổi → chạy lại `.\deploy\windows\setup.ps1`.
3. `nssm restart VitlPianoAI` và `nssm restart VitlPianoBot`.

**Gỡ bỏ:** `.\deploy\windows\uninstall-services.ps1`

---

## 10. Tường lửa

Không cần tạo rule inbound nào. AI Core chỉ bind `127.0.0.1` (nội bộ máy),
bot Node.js không mở cổng. Chỉ cần máy có thể kết nối **ra ngoài** tới `discord.com`
và các trang nhạc (YouTube/SoundCloud/TikTok…) qua HTTPS.

---

## 11. Xử lý sự cố

| Triệu chứng | Nguyên nhân & cách xử lý |
|---|---|
| `Chưa tìm thấy biến môi trường DISCORD_BOT_TOKEN` | Thiếu `.env` hoặc token rỗng → tạo `C:\VitlPianoBot\.env` từ `.env.example` |
| `Chưa tìm thấy Python AI Core tại cổng 5000` | AI Core chưa chạy → `nssm start VitlPianoAI`, xem `logs\ai_core.error.log` |
| `ffprobe: not found` / lỗi đo thời lượng | FFmpeg chưa có trong PATH → mở PowerShell mới sau khi thêm PATH |
| Service `VitlPianoBot` dừng ngay sau khi start | Sai đường dẫn `node` → `nssm edit VitlPianoBot`, kiểm tra `Application` + `AppDirectory` |
| Lỗi `torch` / CUDA không khả dụng | Cài sai bản PyTorch → chạy lại `setup.ps1` (CPU) hoặc `setup.ps1 -Cuda` (GPU) |
| Bot chạy nhưng `/transcript` rất chậm | Kiểm tra số vCPU, đặt `CPU_THREADS=0` (tự động) và `MAX_CONCURRENT_JOBS=1` |
| Slash command không hiện | Đặt `GUILD_ID` để đồng bộ ngay, hoặc chờ vài phút với Global command |

---

## 12. Phương án thay thế

Nếu không muốn dùng NSSM, có thể dùng **WinSW** (https://github.com/winsw/winsw) với cách cấu hình
tương tự: trỏ `AppDirectory` về thư mục dự án và `Application` về `python.exe` / `node.exe`.
Điều kiện quan trọng: **thư mục làm việc (working directory) phải là thư mục gốc dự án**, vì
`config.py` và `dotenv` đọc tệp `.env` theo thư mục làm việc hiện tại.
