<#
.SYNOPSIS
    Cai Vitl Piano Bot thanh Windows Service (tu khoi dong cung Windows, tu chay lai khi loi).

.DESCRIPTION
    Tao 2 service bang NSSM:
      - VitlPianoAI  : Python AI Core  (ai_core\server.py)
      - VitlPianoBot : Node.js Discord Bot (src\index.js), phu thuoc VitlPianoAI

    Chay PowerShell voi quyen Administrator.

.NOTES
    Can tai NSSM truoc: https://nssm.cc/download
    Giai nen va them thu muc chua nssm.exe vao PATH, hoac truyen -NssmPath "C:\nssm\win64\nssm.exe".

.EXAMPLE
    .\deploy\windows\install-services.ps1
    .\deploy\windows\install-services.ps1 -NssmPath "C:\nssm\win64\nssm.exe"
#>

[CmdletBinding()]
param(
    [string]$NssmPath = "nssm",
    [string]$AiServiceName = "VitlPianoAI",
    [string]$BotServiceName = "VitlPianoBot",
    [int]$AiPort = 5000
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Py = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LogDir = Join-Path $ProjectRoot "logs"

if (-not (Test-Path $Py)) {
    throw "Chua co .venv — hay chay .\deploy\windows\setup.ps1 truoc."
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Khong tim thay 'node' trong PATH."
}

$Nssm = $NssmPath
if (-not (Get-Command $NssmPath -ErrorAction SilentlyContinue) -and -not (Test-Path $NssmPath)) {
    throw "Khong tim thay NSSM ('$NssmPath'). Tai tai https://nssm.cc/download roi them vao PATH hoac truyen -NssmPath."
}

$Node = (Get-Command node).Source
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# Xoa service cu (neu co) de cai lai sach se
foreach ($svc in @($BotServiceName, $AiServiceName)) {
    if (Get-Service -Name $svc -ErrorAction SilentlyContinue) {
        Write-Host "==> Go service cu: $svc" -ForegroundColor Yellow
        & $Nssm stop $svc 2>$null | Out-Null
        & $Nssm remove $svc confirm | Out-Null
    }
}

# --- Service 1: Python AI Core ---
Write-Host "==> Tao service $AiServiceName ..." -ForegroundColor Cyan
& $Nssm install $AiServiceName $Py "ai_core\server.py"
& $Nssm set $AiServiceName AppDirectory $ProjectRoot
& $Nssm set $AiServiceName AppStdout (Join-Path $LogDir "ai_core.log")
& $Nssm set $AiServiceName AppStderr (Join-Path $LogDir "ai_core.error.log")
& $Nssm set $AiServiceName AppRotateFiles 1
& $Nssm set $AiServiceName AppRotateOnline 1
& $Nssm set $AiServiceName AppRotateBytes 10485760
& $Nssm set $AiServiceName Start SERVICE_AUTO_START
& $Nssm set $AiServiceName DisplayName "Vitl Piano - Python AI Core"
& $Nssm set $AiServiceName Description "Transkun AI Core (Piano -> MIDI) cho Vitl Piano Bot"

# --- Service 2: Node.js Discord Bot ---
Write-Host "==> Tao service $BotServiceName ..." -ForegroundColor Cyan
& $Nssm install $BotServiceName $Node "src\index.js"
& $Nssm set $BotServiceName AppDirectory $ProjectRoot
& $Nssm set $BotServiceName AppStdout (Join-Path $LogDir "bot.log")
& $Nssm set $BotServiceName AppStderr (Join-Path $LogDir "bot.error.log")
& $Nssm set $BotServiceName AppRotateFiles 1
& $Nssm set $BotServiceName AppRotateOnline 1
& $Nssm set $BotServiceName AppRotateBytes 10485760
& $Nssm set $BotServiceName Start SERVICE_AUTO_START
& $Nssm set $BotServiceName DependOnService $AiServiceName
& $Nssm set $BotServiceName DisplayName "Vitl Piano - Discord Bot"
& $Nssm set $BotServiceName Description "Node.js Discord Bot (discord.js v14) cho Vitl Piano"

# --- Khoi dong ---
Write-Host "==> Khoi dong service..." -ForegroundColor Cyan
& $Nssm start $AiServiceName
Start-Sleep -Seconds 5
& $Nssm start $BotServiceName
Start-Sleep -Seconds 2

Get-Service $AiServiceName, $BotServiceName | Format-Table -AutoSize

# --- Kiem tra AI Core THAT SU lang nghe (service 'Running' chua chac da len cong) ---
Write-Host "==> Kiem tra AI Core tren cong $AiPort ..." -ForegroundColor Cyan
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:$AiPort/health" -UseBasicParsing -TimeoutSec 2 | Out-Null
        $ready = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}
if ($ready) {
    Write-Host "==> AI Core da san sang." -ForegroundColor Green
} else {
    Write-Host "==> CANH BAO: AI Core khong phan hoi tren cong $AiPort -> Bot se bao 'ECONNREFUSED'." -ForegroundColor Red
    foreach ($f in @((Join-Path $LogDir "ai_core.error.log"), (Join-Path $LogDir "ai_core.log"))) {
        if (Test-Path $f) {
            Write-Host "--- 30 dong cuoi: $f ---" -ForegroundColor Yellow
            Get-Content $f -Tail 30 | ForEach-Object { Write-Host "    $_" }
        }
    }
}

Write-Host "==> Hoan tat. Kiem tra log tai: $LogDir" -ForegroundColor Green
