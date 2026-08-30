# ==============================================================================
# VoiceShield Demo Launcher (PowerShell / Windows)
# ==============================================================================

param(
    [string]$ScenarioId = "genuine-executive"
)

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
Set-Location -Path $RootDir

Write-Host "=== VoiceShield Demo Launcher ===" -ForegroundColor Cyan
Write-Host "Selected Scenario: $ScenarioId"

# Check if backend is reachable
$running = $false
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -TimeoutSec 2 -ErrorAction Stop
    if ($health) { $running = $true }
} catch {
    $running = $false
}

if (-not $running) {
    Write-Host "Services are not running. Starting them now..." -ForegroundColor Yellow
    & "$ScriptDir\start.ps1"
}

Write-Host "Triggering scenario '$ScenarioId' via Demo Control API..." -ForegroundColor Cyan
try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/demo/scenarios/$ScenarioId/start?speed=1.0" -Method Post -TimeoutSec 5
    Write-Host "Session Started Successfully!" -ForegroundColor Green
    $resp | ConvertTo-Json -Depth 5 | Write-Host
} catch {
    Write-Error "Failed to start scenario: $_"
}

Write-Host "`n==============================================================================" -ForegroundColor Green
Write-Host " Demo scenario '$ScenarioId' is active!" -ForegroundColor Green
Write-Host " View live streaming decisions in the Dashboard:" -ForegroundColor White
Write-Host " -> http://localhost:5173" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Green
