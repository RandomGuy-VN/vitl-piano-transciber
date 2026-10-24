<#
.SYNOPSIS
    Cài đặt môi trường Vitl Piano Bot trên Windows Server 2025 (chạy native, KHÔNG dùng Docker).

.DESCRIPTION
    Tự dò bản Python 3.12 đang có trên máy (ưu tiên trình khởi chạy "py -3.12"), tạo virtualenv
    ".venv", cài PyTorch + requirements.txt, cài dependencies Node.js và tạo file ".env".

    Script kiểm tra kết quả từng bước và DỪNG NGAY khi một bước thất bại, kèm hướng dẫn sửa.

.NOTES
    Yêu cầu trước khi chạy:
      - Python 3.12 đã cài (nên cài kèm "Python Launcher" `py`)
      - Node.js 20 LTS đã cài và có trong PATH
      - FFmpeg đã cài và có trong PATH (cần ffmpeg + ffprobe)

.EXAMPLE
    .\deploy\windows\setup.ps1
    .\deploy\windows\setup.ps1 -Cuda
    .\deploy\windows\setup.ps1 -PythonExe "C:\Python312\python.exe"
#>

[CmdletBinding()]
param(
    # Cài PyTorch bản CUDA (mặc định: CPU). Dùng nếu VPS có GPU NVIDIA.
    [switch]$Cuda,

    # Chỉ định thủ công đường dẫn python.exe khi máy có nhiều bản Python trùng nhau.
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $ProjectRoot
Write-Host "==> Thu muc du an: $ProjectRoot" -ForegroundColor Cyan

# ------------------------------------------------------------------
# 1. Liệt kê các bản Python máy đang có (giúp chẩn đoán khi bị trùng)
# ------------------------------------------------------------------
if (Get-Command py -ErrorAction SilentlyContinue) {
    Write-Host "==> Cac ban Python ma trinh khoi chay 'py' nhin thay:" -ForegroundColor DarkGray
    try { & py -0p 2>$null | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray } } catch { }
}

# ------------------------------------------------------------------
# 2. Dò bản Python phù hợp (ưu tiên 3.12)
# ------------------------------------------------------------------
function Get-PythonInfo {
    param([string]$Exe, [string[]]$PrefixArgs)
    try {
        $out = & $Exe @PrefixArgs -c "import sys; print(sys.executable + '|' + '.'.join(map(str, sys.version_info[:3])))" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out -match '\|(\d+)\.(\d+)\.(\d+)') {
            return [pscustomobject]@{
                Exe   = $Exe
                Args  = $PrefixArgs
                Path  = ($out -split '\|')[0].Trim()
                Major = [int]$Matches[1]
                Minor = [int]$Matches[2]
            }
        }
    } catch { }
    return $null
}

$candidates = @(
    @{ Exe = "py";      Args = @("-3.12") },
    @{ Exe = "py";      Args = @("-3") },
    @{ Exe = "py";      Args = @() },
    @{ Exe = "python";  Args = @() },
    @{ Exe = "python3"; Args = @() }
)
if ($PythonExe) {
    $candidates = @(@{ Exe = $PythonExe; Args = @() }) + $candidates
}

$python = $null
$fallback = $null
foreach ($cand in $candidates) {
    $exe = $cand.Exe
    $pre = $cand.Args

    if ($exe -ne $PythonExe -and -not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }

    $info = Get-PythonInfo -Exe $exe -PrefixArgs $pre
    if ($null -eq $info) { continue }

    if ($info.Major -eq 3 -and $info.Minor -eq 12) { $python = $info; break }
    if ($info.Major -eq 3 -and $info.Minor -ge 10 -and $null -eq $fallback) { $fallback = $info }
}
if ($null -eq $python) { $python = $fallback }

if ($null -eq $python) {
    throw "Khong tim thay Python 3.10+ hoat dong duoc. Hay cai Python 3.12 (kem 'py' launcher) roi mo PowerShell MOI. Kiem tra bang lenh: py -0p"
}
if ($python.Minor -ne 12) {
    Write-Host "==> CANH BAO: khong tim thay Python 3.12, se dung tam Python $($python.Major).$($python.Minor). Nen cai Python 3.12 de tranh loi thu vien." -ForegroundColor Yellow
}
Write-Host "==> Dung Python : $($python.Path)  (3.$($python.Minor))" -ForegroundColor Green

# ------------------------------------------------------------------
# 3. Tạo virtualenv .venv
# ------------------------------------------------------------------
$Py = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

# .venv cũ bị hỏng (thường do lần chạy trước thất bại) -> xoá để tạo lại
if ((Test-Path ".venv") -and -not (Test-Path $Py)) {
    Write-Host "==> Phat hien .venv bi hong (thieu Scripts\python.exe) -> xoa va tao lai..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force ".venv"
}

if (-not (Test-Path $Py)) {
    Write-Host "==> Tao virtualenv .venv ..." -ForegroundColor Cyan
    $pythonArgs = @($python.Args)
    & $python.Exe @pythonArgs -m venv .venv
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $Py)) {
        throw "Tao virtualenv THAT BAI. Hay chay thu cong: `"$($python.Path)`" -m venv .venv"
    }
}
Write-Host "==> Virtualenv  : $Py" -ForegroundColor Green

# ------------------------------------------------------------------
# 4. Kiểm tra Node.js / FFmpeg
# ------------------------------------------------------------------
foreach ($cmd in @("node", "npm")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        throw "Khong tim thay '$cmd' trong PATH. Hay cai Node.js 20 LTS roi mo PowerShell MOI."
    }
}
Write-Host "==> Node        : $(node --version)" -ForegroundColor Green

foreach ($tool in @("ffmpeg", "ffprobe")) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        Write-Host "==> CANH BAO: chua tim thay '$tool' trong PATH -> bot se loi khi doc thoi luong audio. Hay cai FFmpeg roi mo PowerShell MOI." -ForegroundColor Yellow
    }
}

# ------------------------------------------------------------------
# 5. Cài PyTorch + requirements.txt (Python)
# ------------------------------------------------------------------
Write-Host "==> Nang cap pip ..." -ForegroundColor Cyan
& $Py -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Nang cap pip THAT BAI." }

$torchVariant = if ($Cuda) { "CUDA" } else { "CPU" }
Write-Host "==> Cai PyTorch ($torchVariant) ... (co the mat vai phut)" -ForegroundColor Cyan
if ($Cuda) {
    & $Py -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
} else {
    & $Py -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
}
if ($LASTEXITCODE -ne 0) { throw "Cai PyTorch THAT BAI." }

Write-Host "==> Cai requirements.txt ..." -ForegroundColor Cyan
& $Py -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Cai requirements.txt THAT BAI." }

# ------------------------------------------------------------------
# 6. Cài dependencies Node.js
# ------------------------------------------------------------------
Write-Host "==> Cai dependencies Node.js ..." -ForegroundColor Cyan
if (Test-Path "package-lock.json") {
    npm ci --omit=dev
} else {
    npm install --omit=dev
}
if ($LASTEXITCODE -ne 0) { throw "Cai dependencies Node.js THAT BAI." }

# ------------------------------------------------------------------
# 7. Tạo file .env nếu chưa có
# ------------------------------------------------------------------
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "==> Da tao file .env tu .env.example -> MO FILE .env VA DIEN DISCORD_BOT_TOKEN!" -ForegroundColor Yellow
} else {
    Write-Host "==> File .env da ton tai, bo qua." -ForegroundColor DarkGray
}

Write-Host "==> Cai dat hoan tat!" -ForegroundColor Green
Write-Host "    Buoc tiep theo: .\deploy\windows\run-manual.ps1  (chay thu)" -ForegroundColor Green
