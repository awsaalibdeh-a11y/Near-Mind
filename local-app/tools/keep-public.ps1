# Watchdog for the public NearMind link. Started (minimized) by start-public.ps1; safe to run on its own.
# Every minute: if the public server on 5218 is down, start it; if the permanent workers.dev link doesn't answer,
# start a fresh Cloudflare tunnel and point the link at it. Quick tunnels can expire ("Tunnel not found"), so this
# keeps the link alive for days without anyone touching the computer.
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$log = Join-Path $root "tunnel\live.log"
$wlog = Join-Path $root "tunnel\watchdog.log"
function Say($m) { $line = "$(Get-Date -Format s)  $m"; Write-Host $line; Add-Content -Path $wlog -Value $line }

function Up($url) {
  try { (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 15).StatusCode -eq 200 } catch { $false }
}

function Start-Server {
  Say "public server is down, starting it"
  $env:NM_PUBLIC = "1"; $env:PORT = "5218"
  Start-Process -WindowStyle Minimized -FilePath "python" -ArgumentList "app.py" -WorkingDirectory $root
  Start-Sleep -Seconds 8
}

function Start-Tunnel {
  Say "public link is down, starting a new tunnel"
  Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  if (Test-Path $log) { Remove-Item $log -Force -ErrorAction SilentlyContinue }
  Start-Process -WindowStyle Minimized -FilePath (Join-Path $root "tunnel\cloudflared.exe") `
    -ArgumentList @("tunnel", "--no-autoupdate", "--logfile", $log, "--url", "http://127.0.0.1:5218")
  $url = $null
  for ($i = 0; $i -lt 60 -and -not $url; $i++) {
    Start-Sleep -Seconds 1
    if (Test-Path $log) {
      $m = Select-String -Path $log -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" | Select-Object -First 1
      if ($m) { $url = $m.Matches[0].Value }
    }
  }
  if (-not $url) { Say "no tunnel address yet (offline?), will retry"; return }
  Start-Sleep -Seconds 5
  & (Join-Path $PSScriptRoot "update-link.ps1") -Target $url | Out-Null
  Say "link now forwards to $url"
}

$link = (Get-Content (Join-Path $root "tunnel\link.txt") -ErrorAction SilentlyContinue | Select-Object -First 1)
if (-not $link) { $link = "https://nearmind.awsaa-libdeh.workers.dev" }
Say "watchdog started for $link"
while ($true) {
  if (-not (Up "http://127.0.0.1:5218/api/health")) { Start-Server }
  if (-not (Up "$link/api/health")) {
    Start-Sleep -Seconds 20                      # one more look, so a blip doesn't restart everything
    if (-not (Up "$link/api/health")) { Start-Tunnel }
  }
  Start-Sleep -Seconds 60
}
