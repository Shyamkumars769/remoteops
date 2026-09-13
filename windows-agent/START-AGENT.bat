@echo off
setlocal EnableDelayedExpansion
title RemoteOps Agent
cd /d "%~dp0"

if not exist .venv\Scripts\activate.bat (
  echo Run SETUP.bat first.
  pause
  exit /b 1
)

if exist CONFIG.txt (
  for /f "usebackq tokens=1,* delims==" %%A in ("CONFIG.txt") do (
    set "line=%%A"
    if not "!line:~0,1!"=="#" if not "%%A"=="" set "%%A=%%B"
  )
)

call .venv\Scripts\activate.bat
set SESSION_ENABLED=true
set POLL_INTERVAL=5
if "%SERVER_URL%"=="" set SERVER_URL=http://127.0.0.1:8000
if "%ENROLLMENT_KEY%"=="" set ENROLLMENT_KEY=change-me-enrollment-key

echo Connecting to %SERVER_URL% ...
python -m agent.agent
echo.
echo Agent stopped.
pause
