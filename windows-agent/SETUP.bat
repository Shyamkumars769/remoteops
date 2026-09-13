@echo off
setlocal EnableDelayedExpansion
title RemoteOps Agent Setup
cd /d "%~dp0"

echo ============================================
echo   RemoteOps Agent - Automatic Setup
echo ============================================
echo.

REM --- load CONFIG.txt ---
if not exist CONFIG.txt (
  echo [ERROR] CONFIG.txt not found next to SETUP.bat
  pause
  exit /b 1
)

for /f "usebackq tokens=1,* delims==" %%A in ("CONFIG.txt") do (
  set "line=%%A"
  if not "!line:~0,1!"=="#" if not "%%A"=="" (
    set "%%A=%%B"
  )
)

if "%SERVER_URL%"=="" (
  echo [ERROR] SERVER_URL missing in CONFIG.txt
  pause
  exit /b 1
)
if "%ENROLLMENT_KEY%"=="" (
  echo [ERROR] ENROLLMENT_KEY missing in CONFIG.txt
  pause
  exit /b 1
)

echo Server URL     : %SERVER_URL%
echo Enrollment key : %ENROLLMENT_KEY%
echo.

REM --- find Python ---
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if "%PY%"=="" (
  where python >nul 2>&1 && set "PY=python"
)
if "%PY%"=="" (
  echo [ERROR] Python not found.
  echo Install Python 3 from https://www.python.org/downloads/
  echo IMPORTANT: check "Add Python to PATH" during install.
  echo Then run SETUP.bat again.
  pause
  exit /b 1
)

echo Using: %PY%
%PY% --version
echo.

echo [1/4] Creating virtual environment...
if not exist .venv (
  %PY% -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create venv
    pause
    exit /b 1
  )
)

call .venv\Scripts\activate.bat

echo [2/4] Installing packages...
python -m pip install --upgrade pip >nul
python -m pip install requests psutil websockets pydantic-settings python-dotenv bcrypt
if errorlevel 1 (
  echo [ERROR] pip install failed
  pause
  exit /b 1
)

echo [3/4] Writing start script...
(
  echo @echo off
  echo cd /d "%%~dp0"
  echo call .venv\Scripts\activate.bat
  echo set SERVER_URL=%SERVER_URL%
  echo set ENROLLMENT_KEY=%ENROLLMENT_KEY%
  echo set SESSION_ENABLED=true
  echo set POLL_INTERVAL=5
  echo echo Connecting to %SERVER_URL% ...
  echo python -m agent.agent
  echo pause
) > START-AGENT.bat

echo [4/4] Testing connection to server...
python -c "import os,urllib.request; urllib.request.urlopen(os.environ.get('SERVER_URL','%SERVER_URL%')+'/healthz', timeout=5); print('Server reachable')" 2>nul
if errorlevel 1 (
  echo [WARN] Could not reach %SERVER_URL%/healthz
  echo        Check IP, firewall port 8000, and that server is running.
) else (
  echo Server OK.
)

echo.
echo ============================================
echo   Setup complete.
echo   Double-click START-AGENT.bat to connect.
echo ============================================
echo.
pause
