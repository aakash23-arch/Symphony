# ==============================================================================
# VoiceShield Test Suite Runner (PowerShell / Windows)
# ==============================================================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
Set-Location -Path $RootDir

if (Test-Path ".venv\Scripts\Activate.ps1") {
    & .venv\Scripts\Activate.ps1
}

Write-Host "=== [1/2] Running Backend Test Suite (pytest) ===" -ForegroundColor Cyan
python -m pytest tests/ -v $args

Write-Host "`n=== [2/2] Running Frontend Build & Type Check ===" -ForegroundColor Cyan
Set-Location -Path "$RootDir\frontend"
npm run build
Set-Location -Path $RootDir

Write-Host "`n==============================================================================" -ForegroundColor Green
Write-Host " All VoiceShield automated tests and builds PASSED successfully!" -ForegroundColor Green
Write-Host "==============================================================================" -ForegroundColor Green
