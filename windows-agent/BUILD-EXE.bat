@echo off
title Build remoteops-agent.exe
cd /d "%~dp0"
echo Building one-file agent exe (optional)...
pip install pyinstaller requests psutil websockets pydantic-settings python-dotenv bcrypt
pyinstaller --onefile --name remoteops-agent --paths . agent\agent.py
echo.
echo Output: dist\remoteops-agent.exe
echo Copy that exe + a small start bat with SERVER_URL and ENROLLMENT_KEY to other PCs.
pause
