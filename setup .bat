@echo off
title Remote Platform Agent Setup
color 0A

echo.
echo ============================================
echo   Remote Platform Agent - Auto Setup
echo ============================================
echo.

:: --------------------------------------------------------
:: ASK FOR SERVER IP
:: --------------------------------------------------------
echo Enter your server IP address (from your laptop's ipconfig)
echo Example: 10.194.41.243 or 192.168.1.5
echo.
set /p SERVER_IP="Enter IP: "

if "%SERVER_IP%"=="" (
    echo.
    echo ERROR: No IP entered! Please run setup.bat again.
    pause
    exit /b 1
)

echo.
echo Connecting to: http://%SERVER_IP%:8080
echo.

:: --------------------------------------------------------
:: STEP 1 - Check if Python is installed
:: --------------------------------------------------------
echo [1/6] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Downloading Python installer...
    echo This may take a few minutes - please wait...
    echo.
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile 'python_installer.exe'"
    echo Installing Python...
    python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    timeout /t 15 /nobreak >nul
    del python_installer.exe
    echo Python installed successfully!
    echo.
) else (
    echo Python is already installed!
)

echo.

:: --------------------------------------------------------
:: STEP 2 - Verify Python works
:: --------------------------------------------------------
echo [2/6] Verifying Python...
python --version
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Python still not found after install.
    echo Please install Python manually from https://python.org
    echo Make sure to check "Add Python to PATH" during install!
    echo.
    pause
    exit /b 1
)

echo.

:: --------------------------------------------------------
:: STEP 3 - Install required packages
:: --------------------------------------------------------
echo [3/6] Installing required packages...
echo Installing requests...
python -m pip install requests --quiet
echo Installing psutil...
python -m pip install psutil --quiet
echo Packages installed successfully!

echo.

:: --------------------------------------------------------
:: STEP 4 - Check files exist
:: --------------------------------------------------------
echo [4/6] Checking agent files...

if not exist "agent\" (
    echo.
    echo ERROR: agent folder not found!
    echo Make sure setup.bat is in the same folder as the agent folder.
    echo.
    echo Correct structure:
    echo   other pc/
    echo   agent/
    echo   start_agent.py
    echo   setup.bat
    echo.
    pause
    exit /b 1
)

echo Agent folder found!

echo.

:: --------------------------------------------------------
:: STEP 5 - Create start_agent.py with the entered IP
:: --------------------------------------------------------
echo [5/6] Configuring agent with server IP: %SERVER_IP%...

(
echo import sys
echo import os
echo sys.path.insert^(0, os.path.dirname^(__file__^)^)
echo from agent.agent import Agent
echo Agent^(server_url="http://%SERVER_IP%:8080"^).run^(^)
) > start_agent.py

echo Agent configured successfully!

echo.

:: --------------------------------------------------------
:: STEP 6 - Start the agent
:: --------------------------------------------------------
echo [6/6] Starting Remote Platform Agent...
echo.
echo ============================================
echo   Agent is now running!
echo   Server: http://%SERVER_IP%:8080
echo   DO NOT close this window.
echo   The agent will connect to the server.
echo ============================================
echo.

python start_agent.py

:: If agent stops show error
echo.
echo ============================================
echo   Agent stopped!
echo   Check the error message above.
echo   Make sure the server is running on:
echo   http://%SERVER_IP%:8080
echo ============================================
echo.
pause
