@echo off
setlocal enabledelayedexpansion

REM ==============================================================================
REM VoiceShield Test Suite Runner (Windows Batch)
REM ==============================================================================

cd /d "%~dp0\.."

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

echo === [1/2] Running Backend Test Suite (pytest) ===
python -m pytest tests/ -v
if %ERRORLEVEL% NEQ 0 (
    echo Backend tests failed.
    exit /b 1
)

echo.
echo === [2/2] Running Frontend Build ^& Type Check ===
cd frontend
call npm run build
if %ERRORLEVEL% NEQ 0 (
    echo Frontend build failed.
    exit /b 1
)
cd ..

echo.
echo ==============================================================================
echo  All VoiceShield automated tests and builds PASSED successfully!
echo ==============================================================================
