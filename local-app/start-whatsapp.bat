@echo off
cd /d "%~dp0"
for /f "usebackq tokens=1,* delims==" %%a in (".env") do if /i "%%a"=="WA_PHONE" set "WA_PHONE=%%b"
cd bridge
title NearMind WhatsApp bridge
node bridge.js
pause
