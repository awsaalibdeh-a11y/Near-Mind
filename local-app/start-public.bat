@echo off
rem NearMind public link from this computer: a public-mode server on port 5218 plus a free Cloudflare tunnel.
rem The link works only while this window is open and the computer is awake. Closing it takes the site offline.
cd /d "%~dp0"
title NearMind public link
if not exist "tunnel\cloudflared.exe" (
  echo tunnel\cloudflared.exe is missing. Download cloudflared for Windows from Cloudflare and put it in the tunnel folder.
  pause
  exit /b 1
)
start "NearMind public server (keep open)" /min cmd /k "set NM_PUBLIC=1&& set PORT=5218&& python app.py"
timeout /t 6 /nobreak >nul
echo.
echo  Starting the public link. In a few seconds a box appears below with an address like
echo      https://something-something.trycloudflare.com
echo  That is your live NearMind link. Chat history:  that address + /chat/jump
echo  Keep this window open. Press Ctrl+C here to stop the link.
echo.
tunnel\cloudflared.exe tunnel --no-autoupdate --url http://127.0.0.1:5218
pause
