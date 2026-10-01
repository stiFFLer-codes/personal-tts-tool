@echo off
setlocal
cd /d "%~dp0"
echo.
echo   === IELTS Listening Studio : one-time setup ===
echo.

rem Find a Python the voice engine supports (3.10 - 3.13). Newest first, 3.12 preferred.
set "PY="
for %%V in (3.12 3.13 3.11 3.10) do (
  if not defined PY ( py -%%V -c "pass" >nul 2>nul && set "PY=py -%%V" )
)
if not defined PY ( python -c "import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,13) else 1)" >nul 2>nul && set "PY=python" )
if not defined PY goto :nopython
echo   Using: %PY%

if not exist ".venv\Scripts\python.exe" (
  echo   Creating virtual environment...
  %PY% -m venv .venv || goto :fail
)
echo   Installing the voice engine (kokoro-onnx)...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q --upgrade pip
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt || goto :fail
echo.
echo   Downloading the voice model (one time only)...
".venv\Scripts\python.exe" -m ielts_tts.download_models %* || goto :fail
echo.
echo   All set! Double-click run.bat to start practising.
echo.
pause
exit /b 0

:nopython
echo   Python 3.10 - 3.13 was not found.
echo   Install Python 3.12 from https://www.python.org/downloads/
echo   and tick "Add python.exe to PATH" during install, then run setup.bat again.
pause
exit /b 1

:fail
echo.
echo   Setup failed - see the message above. Running setup.bat again is safe.
pause
exit /b 1
