#Requires -Version 5.1
<#
.SYNOPSIS
    One-shot installer for Tech Pulse News.
    Run once from any PowerShell window - no admin required.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

# 1. Python version gate
try {
    $ver = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
} catch {
    Write-Error "Python not found on PATH. Install Python 3.11+ and try again."
    exit 1
}
if (-not $ver) { Write-Error "Python not found on PATH. Install Python 3.11+ and try again."; exit 1 }
if ([version]$ver -lt [version]"3.11") {
    Write-Error "Python $ver found but 3.11+ is required."
    exit 1
}
Write-Host "Python $ver OK" -ForegroundColor Green

# 2. Create venv
$Venv    = Join-Path $Root "venv"
$Pip     = Join-Path $Venv "Scripts\pip.exe"
$Python  = Join-Path $Venv "Scripts\python.exe"
$Pythonw = Join-Path $Venv "Scripts\pythonw.exe"

if (-not (Test-Path $Venv)) {
    Write-Host "Creating virtual environment..."
    python -m venv $Venv
}

# 3. Install dependencies
Write-Host "Installing dependencies..."
& $Pip install -r (Join-Path $Root "requirements.txt") -q

# 4. Install Playwright Chromium
Write-Host "Installing Playwright Chromium..."
& $Python -m playwright install chromium

# 5. Copy .env if missing
$EnvFile    = Join-Path $Root ".env"
$EnvExample = Join-Path $Root ".env.example"
if (-not (Test-Path $EnvFile)) {
    Copy-Item $EnvExample $EnvFile
    Write-Host ".env created from .env.example - edit it before launching!" -ForegroundColor Yellow
} else {
    Write-Host ".env already exists - skipping copy" -ForegroundColor Cyan
}

# 6. Create logs directory
New-Item -Force -ItemType Directory (Join-Path $Root "logs") | Out-Null

# 7. Windows Startup shortcut (no admin - user's own Startup folder)
$StartupDir = [Environment]::GetFolderPath("Startup")
$LnkPath    = Join-Path $StartupDir "TechPulseNews.lnk"
$WS  = New-Object -ComObject WScript.Shell
$Lnk = $WS.CreateShortcut($LnkPath)
$Lnk.TargetPath       = $Pythonw
$Lnk.Arguments        = "`"$(Join-Path $Root 'app.py')`""
$Lnk.WorkingDirectory = $Root
$Lnk.Description      = "Tech Pulse News - local AI news agent"
$Lnk.Save()
Write-Host "Startup shortcut created: $LnkPath" -ForegroundColor Green

Write-Host ""
Write-Host "-----------------------------------------" -ForegroundColor Cyan
Write-Host " Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host " Next steps:" -ForegroundColor White
Write-Host "  1. Open LM Studio -> load phi-3.5-mini-instruct -> Start Server"
Write-Host "  2. Edit .env:  notepad `"$EnvFile`""
Write-Host "  3. Launch now: & `"$Pythonw`" `"$(Join-Path $Root 'app.py')`""
Write-Host "-----------------------------------------" -ForegroundColor Cyan
