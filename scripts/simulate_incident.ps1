# B3 — Incident de LABORATOIRE (Windows / PowerShell). Usage : .\scripts\simulate_incident.ps1 -N 30
param([int]$N = 30)
Write-Host "[1/3] $(Get-Date -AsUTC -Format s)Z Recréation de l'API avec SIMULATE_FAILURE=true"
$env:SIMULATE_FAILURE = "true"
docker compose up -d --force-recreate api
Remove-Item Env:SIMULATE_FAILURE
Start-Sleep -Seconds 5
Write-Host "[2/3] $N appels à /orders"
1..$N | ForEach-Object {
  try { $r = Invoke-WebRequest http://localhost:8000/orders -UseBasicParsing; Write-Host "  appel $_ → HTTP $($r.StatusCode)" }
  catch { Write-Host "  appel $_ → HTTP 500 simulé" }
  Start-Sleep -Seconds 1
}
Write-Host "[3/3] Attendre ~1 min puis : python -m aiops.detector"
