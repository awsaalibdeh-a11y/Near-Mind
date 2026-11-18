# Point the permanent workers.dev link at the current tunnel address (and keep the proxy secret in sync).
# Usage: powershell -File tools\update-link.ps1 -Target https://....trycloudflare.com
param([Parameter(Mandatory = $true)][string]$Target)
$ErrorActionPreference = "Continue"     # wrangler prints notes on stderr; success is judged by the workers.dev URL in its output
$root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $root "worker")

if ($Target -notmatch '^https://[a-z0-9-]+\.trycloudflare\.com/?$') { Write-Host "That doesn't look like a tunnel address: $Target"; exit 1 }

Write-Host "Updating the permanent link to forward to $Target ..."
$out = & npx wrangler deploy --var "TARGET:$Target" 2>&1 | Out-String
$link = [regex]::Match($out, "https://[a-z0-9.-]+\.workers\.dev").Value
if (-not $link) { Write-Host $out; Write-Host "Deploy failed (see above)."; exit 1 }

# keep the shared secret in the Worker the same as NM_PROXY_SECRET in .env (so per-visitor limits work)
$secret = ((Get-Content (Join-Path $root ".env") | Where-Object { $_ -match '^NM_PROXY_SECRET=' } | Select-Object -First 1) -replace '^NM_PROXY_SECRET=', '').Trim()
$has = (& npx wrangler secret list 2>&1 | Out-String) -match 'PROXY_SECRET'
if ($secret -and -not $has) {          # only the first time; it never changes after that
  $tmp = New-TemporaryFile
  [IO.File]::WriteAllText($tmp, $secret)
  cmd /c "npx wrangler secret put PROXY_SECRET < `"$tmp`"" 2>&1 | Out-Null
  Remove-Item $tmp -Force
}

Set-Content -Path (Join-Path $root "tunnel\link.txt") -Value $link -Encoding utf8
Write-Host ""
Write-Host "  Your permanent NearMind link:  $link"
Write-Host "  Chat history:                  $link/chat/jump"
Write-Host ""
Write-Host "  Keep this computer on and awake. Closing the minimized server or tunnel windows takes the site offline."
