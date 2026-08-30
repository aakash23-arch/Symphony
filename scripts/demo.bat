@echo off
setlocal enabledelayedexpansion

REM ==============================================================================
REM VoiceShield Demo Launcher (Windows Batch)
REM ==============================================================================

cd /d "%~dp0\.."

set SCENARIO=%1
if "%SCENARIO%"=="" set SCENARIO=genuine-executive

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0demo.ps1" -ScenarioId "%SCENARIO%"
