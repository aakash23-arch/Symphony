# ==============================================================================
# VoiceShield Setup Script (PowerShell / Windows)
# ==============================================================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
Set-Location -Path $RootDir

Write-Host "=== [1/5] Checking Prerequisites ===" -ForegroundColor Cyan
try {
    $pythonVer = python --version 2>&1
    Write-Host "Python: $pythonVer"
} catch {
    Write-Error "Python 3.10+ is required but not found on PATH."
    exit 1
}

try {
    $nodeVer = node --version 2>&1
    $npmVer = npm --version 2>&1
    Write-Host "Node:   $nodeVer"
    Write-Host "npm:    $npmVer"
} catch {
    Write-Error "Node.js 18+ and npm are required but not found on PATH."
    exit 1
}

Write-Host "`n=== [2/5] Setting up Environment Configuration ===" -ForegroundColor Cyan
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..."
    Copy-Item ".env.example" ".env"
} else {
    Write-Host ".env already exists, preserving existing configuration."
}

if (-not (Test-Path "data")) { New-Item -ItemType Directory -Path "data" | Out-Null }
if (-not (Test-Path ".run")) { New-Item -ItemType Directory -Path ".run" | Out-Null }

Write-Host "`n=== [3/5] Installing Backend Dependencies ===" -ForegroundColor Cyan
if (-not (Test-Path ".venv")) {
    Write-Host "Creating Python virtual environment in .venv..."
    python -m venv .venv
}

if (Test-Path ".venv\Scripts\Activate.ps1") {
    & .venv\Scripts\Activate.ps1
}

python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install -e .

Write-Host "`n=== [4/5] Generating Audio Demo Fixtures ===" -ForegroundColor Cyan
python scripts/make_demo_fixtures.py

Write-Host "`n=== [5/5] Installing Frontend Dependencies ===" -ForegroundColor Cyan
Set-Location -Path "$RootDir\frontend"
npm install
Set-Location -Path $RootDir

Write-Host "`n==============================================================================" -ForegroundColor Green
Write-Host " VoiceShield setup completed successfully!" -ForegroundColor Green
Write-Host " Next steps:"
Write-Host "   1. Start services:  .\scripts\start.ps1 (or scripts\start.bat)"
Write-Host "   2. Open Dashboard:  http://localhost:5173"
Write-Host "   3. Run tests:       .\scripts\test.ps1  (or scripts\test.bat)"
Write-Host "==============================================================================" -ForegroundColor Green
