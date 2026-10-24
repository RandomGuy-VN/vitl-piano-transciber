<#
.SYNOPSIS
    Chay thu Vitl Piano Bot bang tay (khong cai service) de kiem tra truoc khi dua vao van hanh.

.DESCRIPTION
    Khoi dong Python AI Core, ghi log ra logs\ai_core.log, doi cho AI Core san sang,
    roi chay Node.js Discord Bot ngay tren cua so hien tai.
    Nhan Ctrl+C de dung ca Bot va AI Core.

    Neu AI Core khong len duoc, script IN 30 DONG LOG CUOI va DUNG LAI (khong chay Bot
    trong tinh trang hong) de ban thay ngay nguyen nhan.

.EXAMPLE
    .\deploy\windows\run-manual.ps1
#>

[CmdletBinding()]
param(
    [int]$AiPort = 5000,
    [int]$AiStartupTimeoutSec = 180
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $ProjectRoot
$Py = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Py)) {
    throw "Chua co .venv — hay chay .\deploy\windows\setup.ps1 truoc."
}
if (-not (Test-Path ".env")) {
    throw "Chua co file .env — hay copy .env.example thanh .env va dien DISCORD_BOT_TOKEN."
}

$LogDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$AiOut = Join-Path $LogDir "ai_core.log"
$AiErr = Join-Path $LogDir "ai_core.error.log"

# 1. Khoi dong Python AI Core (ghi log ra file de chan doan khi loi)
Write-Host "==> Khoi dong Python AI Core (log: $AiOut) ..." -ForegroundColor Cyan
$aiProc = Start-Process -FilePath $Py -ArgumentList "ai_core\server.py" `
    -WorkingDirectory $ProjectRoot -NoNewWindow -PassThru `
    -RedirectStandardOutput $AiOut -RedirectStandardError $AiErr

# 2. Doi AI Core san sang
Write-Host "==> Doi AI Core san sang tren cong $AiPort (toi da $AiStartupTimeoutSec giay) ..." -ForegroundColor Cyan
$ready = $false
$deadline = (Get-Date).AddSeconds($AiStartupTimeoutSec)
while ((Get-Date) -lt $deadline) {
    if ($aiProc.HasExited) { break }
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:$AiPort/health" -UseBasicParsing -TimeoutSec 2 | Out-Null
        $ready = $true
        break
    } catch {
        Start-Sleep -Milliseconds 500
    }
}

if (-not $ready) {
    Write-Host "==> AI CORE KHONG KHOI DONG DUOC (cong $AiPort khong phan hoi)." -ForegroundColor Red
    if ($aiProc.HasExited) {
        Write-Host "    Tien trinh AI Core da thoat (exit code $($aiProc.ExitCode))." -ForegroundColor Red
    }
    foreach ($f in @($AiErr, $AiOut)) {
        if (Test-Path $f) {
            Write-Host "--- 30 dong cuoi: $f ---" -ForegroundColor Yellow
            Get-Content $f -Tail 30 | ForEach-Object { Write-Host "    $_" }
        }
    }
    Write-Host "==> Da dung lai (Bot khong duoc khoi dong). Xem loi truc tiep bang lenh:" -ForegroundColor Yellow
    Write-Host "    .\.venv\Scripts\python.exe ai_core\server.py" -ForegroundColor Yellow
    if (-not $aiProc.HasExited) { Stop-Process -Id $aiProc.Id -Force }
    exit 1
}
Write-Host "==> AI Core da san sang." -ForegroundColor Green

# 3. Chay Node.js Discord Bot
Write-Host "==> Khoi dong Node.js Discord Bot (Ctrl+C de dung)..." -ForegroundColor Cyan
try {
    node src\index.js
} finally {
    if (-not $aiProc.HasExited) {
        Write-Host "==> Dung AI Core..." -ForegroundColor Cyan
        Stop-Process -Id $aiProc.Id -Force
    }
}
