@echo off
setlocal enabledelayedexpansion

REM ==============================================================================
REM VoiceShield Start Script (Windows Batch)
REM ==============================================================================

cd /d "%~dp0\.."

if not exist ".run" mkdir .run
if not exist "data" mkdir data

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

echo === Starting VoiceShield Services ===

echo Starting backend API server in background...
start "VoiceShield Backend" /min cmd /c "python -m uvicorn voiceshield.api.app:app --host 127.0.0.1 --port 8000 > .run\backend.log 2>&1"

echo Starting frontend dev server in background...
start "VoiceShield Frontend" /min cmd /c "cd frontend && npm run dev -- --host 127.0.0.1 --port 5173 > ..\.run\frontend.log 2>&1"

echo Waiting for services to initialize...
timeout /t 3 /nobreak >nul

echo.
echo ==============================================================================
echo  VoiceShield Services Launched!
echo  - Dashboard:  http://localhost:5173
echo  - API / Docs: http://localhost:8000/docs
echo  - Health:     http://localhost:8000/health
echo.
echo  Target Workflow:
echo    1. Open http://localhost:5173
echo    2. Under DEMO MODE, choose a test scenario
echo    3. Click 'Start Scenario Call'
echo.
echo  To stop: scripts\stop.bat
echo ==============================================================================
