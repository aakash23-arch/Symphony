# ==============================================================================
# VoiceShield Start Script (PowerShell / Windows)
# ==============================================================================

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
Set-Location -Path $RootDir

if (-not (Test-Path ".run")) { New-Item -ItemType Directory -Path ".run" | Out-Null }
if (-not (Test-Path "data")) { New-Item -ItemType Directory -Path "data" | Out-Null }

if (Test-Path ".venv\Scripts\Activate.ps1") {
    & .venv\Scripts\Activate.ps1
}

Write-Host "=== Starting VoiceShield Services ===" -ForegroundColor Cyan

# Start Backend
$backendRunning = $false
if (Test-Path ".run\backend.pid") {
    $oldPid = Get-Content ".run\backend.pid" -ErrorAction SilentlyContinue
    if ($oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) {
        Write-Host "Backend is already running (PID: $oldPid)."
        $backendRunning = $true
    }
}

if (-not $backendRunning) {
    Write-Host "Starting backend API server on http://localhost:8000..."
    $backendProcess = Start-Process python -ArgumentList "-m", "uvicorn", "voiceshield.api.app:app", "--host", "127.0.0.1", "--port", "8000" -RedirectStandardOutput ".run\backend.log" -RedirectStandardError ".run\backend.err.log" -PassThru -NoNewWindow
    Set-Content -Path ".run\backend.pid" -Value $backendProcess.Id
}

# Start Frontend
$frontendRunning = $false
if (Test-Path ".run\frontend.pid") {
    $oldPid = Get-Content ".run\frontend.pid" -ErrorAction SilentlyContinue
    if ($oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) {
        Write-Host "Frontend is already running (PID: $oldPid)."
        $frontendRunning = $true
    }
}

if (-not $frontendRunning) {
    Write-Host "Starting frontend dev server on http://localhost:5173..."
    $frontendProcess = Start-Process cmd -ArgumentList "/c", "cd frontend && npm run dev -- --host 127.0.0.1 --port 5173" -RedirectStandardOutput ".run\frontend.log" -RedirectStandardError ".run\frontend.err.log" -PassThru -NoNewWindow
    Set-Content -Path ".run\frontend.pid" -Value $frontendProcess.Id
}

Write-Host "Waiting for services to become ready..." -ForegroundColor Yellow
$healthy = $false
for ($i = 0; $i -lt 25; $i++) {
    Start-Sleep -Seconds 1
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -TimeoutSec 2 -ErrorAction Stop
        if ($resp -and ($resp.status -eq "healthy" -or $resp.status -eq "degraded")) {
            $healthy = $true
            break
        }
    } catch {
        # Retry
    }
}

if ($healthy) {
    Write-Host "`n==============================================================================" -ForegroundColor Green
    Write-Host " VoiceShield is LIVE and ready!" -ForegroundColor Green
    Write-Host " - Dashboard:  http://localhost:5173" -ForegroundColor White
    Write-Host " - API / Docs: http://localhost:8000/docs" -ForegroundColor White
    Write-Host " - Health:     http://localhost:8000/health" -ForegroundColor White
    Write-Host "`n Target Workflow:" -ForegroundColor Cyan
    Write-Host "   1. Open http://localhost:5173 in your browser"
    Write-Host "   2. Under the DEMO MODE panel, select a scenario (e.g. Scenario 1, 2, or 3)"
    Write-Host "   3. Click 'Start Scenario Call'"
    Write-Host "`n To stop services: .\scripts\stop.ps1" -ForegroundColor Yellow
    Write-Host "==============================================================================" -ForegroundColor Green
} else {
    Write-Warning "Backend healthcheck timed out. Check .run\backend.log and .run\backend.err.log for details."
}
