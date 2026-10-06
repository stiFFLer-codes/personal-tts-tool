@echo off
cd /d "%~dp0"
title Listening Studio
if not exist ".venv\Scripts\python.exe" (
  echo   Please run setup.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m ielts_tts %*
pause
