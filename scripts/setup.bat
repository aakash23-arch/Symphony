@echo off
setlocal enabledelayedexpansion

REM ==============================================================================
REM VoiceShield Setup Script (Windows Batch)
REM ==============================================================================

cd /d "%~dp0\.."

echo === [1/5] Checking Prerequisites ===
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python 3.10+ is required but not found on PATH.
    exit /b 1
)

node --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Node.js 18+ is required but not found on PATH.
    exit /b 1
)

npm --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: npm is required but not found on PATH.
    exit /b 1
)

echo Python:
python --version
echo Node:
node --version
echo npm:
call npm --version

echo.
echo === [2/5] Setting up Environment Configuration ===
if not exist ".env" (
    echo Creating .env from .env.example...
    copy .env.example .env >nul
) else (
    echo .env already exists, preserving existing configuration.
)
if not exist "data" mkdir data
if not exist ".run" mkdir .run

echo.
echo === [3/5] Installing Backend Dependencies ===
if not exist ".venv" (
    echo Creating Python virtual environment in .venv...
    python -m venv .venv
)

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install -e .

echo.
echo === [4/5] Generating Audio Demo Fixtures ===
python scripts/make_demo_fixtures.py

echo.
echo === [5/5] Installing Frontend Dependencies ===
cd frontend
call npm install
cd ..

echo.
echo ==============================================================================
echo  VoiceShield setup completed successfully!
echo  Next steps:
echo    1. Start services:  scripts\start.bat (or scripts\start.ps1)
echo    2. Open Dashboard:  http://localhost:5173
echo    3. Run tests:       scripts\test.bat  (or scripts\test.ps1)
echo ==============================================================================
