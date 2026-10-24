<#
.SYNOPSIS
    Chay thu Vitl Piano Bot bang tay (khong cai service) de kiem tra truoc khi dua vao van hanh.

.DESCRIPTION
    Mo Python AI Core trong mot cua so rieng, doi cho AI Core san sang,
    roi chay Node.js Discord Bot ngay tren cua so hien tai.
    Nhan Ctrl+C de dung Node.js Bot; dong cua so AI Core de dung AI Core.

.EXAMPLE
    .\deploy\windows\run-manual.ps1
#>

[CmdletBinding()]
param(
    [int]$AiPort = 5000
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

# 1. Khoi dong Python AI Core trong cua so rieng
Write-Host "==> Khoi dong Python AI Core (cua so rieng)..." -ForegroundColor Cyan
Start-Process -FilePath $Py -ArgumentList "ai_core\server.py" -WorkingDirectory $ProjectRoot

# 2. Doi AI Core san sang
Write-Host "==> Doi AI Core san sang tren cong $AiPort ..." -ForegroundColor Cyan
$ready = $false
for ($i = 0; $i -lt 40; $i++) {
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:$AiPort/health" -UseBasicParsing -TimeoutSec 2 | Out-Null
        $ready = $true
        break
    } catch {
        Start-Sleep -Milliseconds 500
    }
}
if ($ready) {
    Write-Host "==> AI Core da san sang." -ForegroundColor Green
} else {
    Write-Host "==> AI Core chua phan hoi — van tiep tuc khoi dong Bot..." -ForegroundColor Yellow
}

# 3. Chay Node.js Discord Bot
Write-Host "==> Khoi dong Node.js Discord Bot (Ctrl+C de dung)..." -ForegroundColor Cyan
node src\index.js
