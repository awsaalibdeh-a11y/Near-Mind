@echo off
cd /d "%~dp0"
set PORT=5215
rem WhatsApp is off for now. To turn it on, also run start-whatsapp.bat
start "" http://localhost:5215
python app.py
pause
