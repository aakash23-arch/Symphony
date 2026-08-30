# ==============================================================================
# VoiceShield Stop Script (PowerShell / Windows)
# ==============================================================================

$ErrorActionPreference = "SilentlyContinue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
Set-Location -Path $RootDir

Write-Host "=== Stopping VoiceShield Services ===" -ForegroundColor Cyan

if (Test-Path ".run\backend.pid") {
    $pidNum = Get-Content ".run\backend.pid"
    if ($pidNum) {
        Write-Host "Stopping Backend (PID: $pidNum)..."
        Stop-Process -Id $pidNum -Force -ErrorAction SilentlyContinue
    }
    Remove-Item ".run\backend.pid" -Force -ErrorAction SilentlyContinue
}

if (Test-Path ".run\frontend.pid") {
    $pidNum = Get-Content ".run\frontend.pid"
    if ($pidNum) {
        Write-Host "Stopping Frontend (PID: $pidNum)..."
        Stop-Process -Id $pidNum -Force -ErrorAction SilentlyContinue
    }
    Remove-Item ".run\frontend.pid" -Force -ErrorAction SilentlyContinue
}

# Stop any lingering processes on ports 8000 and 5173
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.OwningProcess -gt 0) {
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }
}
Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.OwningProcess -gt 0) {
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "All VoiceShield services stopped." -ForegroundColor Green
