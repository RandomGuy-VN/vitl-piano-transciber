<#
.SYNOPSIS
    Cài đặt môi trường Vitl Piano Bot trên Windows Server 2025 (chạy native, KHÔNG dùng Docker).

.DESCRIPTION
    Tạo virtualenv Python, cài PyTorch + requirements.txt, cài dependencies Node.js
    và tạo file .env từ .env.example nếu chưa có.

    Chạy script này MỘT LẦN trong thư mục gốc dự án bằng PowerShell (Run as Administrator).

.NOTES
    Yêu cầu trước khi chạy:
      - Python 3.12 đã cài và có trong PATH  (tùy chọn: "Add python.exe to PATH")
      - Node.js 20 LTS đã cài và có trong PATH
      - FFmpeg đã cài và có trong PATH (cần cho ffprobe / tách audio)

.EXAMPLE
    .\deploy\windows\setup.ps1
    .\deploy\windows\setup.ps1 -Cuda      # nếu VPS có GPU NVIDIA
#>

[CmdletBinding()]
param(
    # Mặc định cài PyTorch bản CPU. Dùng -Cuda nếu máy có GPU NVIDIA.
    [switch]$Cuda
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $ProjectRoot
Write-Host "==> Thu muc du an: $ProjectRoot" -ForegroundColor Cyan

# 1. Kiem tra cong cu bat buoc
foreach ($cmd in @("python", "node", "npm")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        throw "Khong tim thay '$cmd' trong PATH. Hay cai Python 3.12 va Node.js 20 LTS truoc."
    }
}
Write-Host "==> Python: $(python --version 2>&1)"
Write-Host "==> Node  : $(node --version)"

# 2. Tao virtualenv
if (-not (Test-Path ".venv")) {
    Write-Host "==> Tao virtualenv .venv ..." -ForegroundColor Cyan
    python -m venv .venv
}
$Py = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

# 3. Cai PyTorch + cac thu vien Python
Write-Host "==> Cai PyTorch (CPU)... (co the mat vai phut)" -ForegroundColor Cyan
& $Py -m pip install --upgrade pip
if ($Cuda) {
    & $Py -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
} else {
    & $Py -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
}
Write-Host "==> Cai requirements.txt ..." -ForegroundColor Cyan
& $Py -m pip install -r requirements.txt

# 4. Cai dependencies Node.js
Write-Host "==> Cai dependencies Node.js ..." -ForegroundColor Cyan
if (Test-Path "package-lock.json") {
    npm ci --omit=dev
} else {
    npm install --omit=dev
}

# 5. Tao file .env neu chua co
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "==> Da tao file .env tu .env.example -> MO FILE .env VA DIEN DISCORD_BOT_TOKEN!" -ForegroundColor Yellow
} else {
    Write-Host "==> File .env da ton tai, bo qua." -ForegroundColor DarkGray
}

Write-Host "==> Cai dat hoan tat!" -ForegroundColor Green
Write-Host "    Buoc tiep theo: .\deploy\windows\run-manual.ps1  (chay thu)" -ForegroundColor Green
