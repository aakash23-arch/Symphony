@echo off
setlocal enabledelayedexpansion

REM ==============================================================================
REM VoiceShield Stop Script (Windows Batch)
REM ==============================================================================

cd /d "%~dp0\.."

echo === Stopping VoiceShield Services ===

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1"

echo Done.
