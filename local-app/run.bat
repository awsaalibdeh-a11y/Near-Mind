@echo off
cd /d "%~dp0"
set PORT=5215
start "NearMind bridge" cmd /c "%~dp0start-whatsapp.bat"
start "" http://localhost:5215
python app.py
pause
