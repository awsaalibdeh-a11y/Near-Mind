@echo off
rem NearMind public site: starts the public server and the tunnel, then points the permanent workers.dev link at it.
rem The link stays the same every time; the computer must stay on and awake for the site to work.
cd /d "%~dp0"
title NearMind public link
if not exist "tunnel\cloudflared.exe" (
  echo tunnel\cloudflared.exe is missing. Download cloudflared for Windows from Cloudflare and put it in the tunnel folder.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\start-public.ps1"
pause
