param([int]$Seconds = 300)
$end = (Get-Date).AddSeconds($Seconds)
Write-Host "Trafic nominal sur /orders pendant $Seconds s…"
while ((Get-Date) -lt $end) { try { Invoke-WebRequest http://localhost:8000/orders -UseBasicParsing | Out-Null } catch {}; Start-Sleep -Milliseconds 500 }
