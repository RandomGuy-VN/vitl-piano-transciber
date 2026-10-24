<#
.SYNOPSIS
    Go bo cac Windows Service cua Vitl Piano Bot.

.DESCRIPTION
    Dung va xoa 2 service VitlPianoBot va VitlPianoAI (khong xoa ma nguon hay .venv).
    Chay PowerShell voi quyen Administrator.

.EXAMPLE
    .\deploy\windows\uninstall-services.ps1
#>

[CmdletBinding()]
param(
    [string]$NssmPath = "nssm",
    [string]$AiServiceName = "VitlPianoAI",
    [string]$BotServiceName = "VitlPianoBot"
)

$ErrorActionPreference = "Stop"

$Nssm = $NssmPath
if (-not (Get-Command $NssmPath -ErrorAction SilentlyContinue) -and -not (Test-Path $NssmPath)) {
    throw "Khong tim thay NSSM ('$NssmPath'). Them vao PATH hoac truyen -NssmPath."
}

foreach ($svc in @($BotServiceName, $AiServiceName)) {
    if (Get-Service -Name $svc -ErrorAction SilentlyContinue) {
        Write-Host "==> Dung va go service: $svc" -ForegroundColor Yellow
        & $Nssm stop $svc 2>$null | Out-Null
        & $Nssm remove $svc confirm | Out-Null
    } else {
        Write-Host "==> Khong tim thay service: $svc (bo qua)" -ForegroundColor DarkGray
    }
}

Write-Host "==> Da go bo cac service." -ForegroundColor Green
