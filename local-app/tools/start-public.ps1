# NearMind public site: public-mode server (port 5218) + Cloudflare tunnel + the permanent workers.dev link.
# Run by start-public.bat. The tunnel address changes on every start; this script points the workers.dev Worker at it,
# so the link you shared never changes.
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$log = Join-Path $root "tunnel\live.log"

Write-Host "Starting the NearMind public server on port 5218..."
$env:NM_PUBLIC = "1"; $env:PORT = "5218"
Start-Process -WindowStyle Minimized -FilePath "python" -ArgumentList "app.py" -WorkingDirectory $root
Start-Sleep -Seconds 6

Write-Host "Starting the Cloudflare tunnel..."
if (Test-Path $log) { Remove-Item $log -Force }
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
if (-not $url) { Write-Host "The tunnel didn't give an address. Check your internet connection and run this again."; exit 1 }
Write-Host "Tunnel address: $url"

& (Join-Path $PSScriptRoot "update-link.ps1") -Target $url

# keep it alive: restarts the server or tunnel by itself if either goes down (quick tunnels can expire)
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -like '*keep-public.ps1*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Process -WindowStyle Minimized -FilePath "powershell" -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "keep-public.ps1"))
Write-Host "  A watchdog window is running too: it brings the link back by itself if it ever drops."
