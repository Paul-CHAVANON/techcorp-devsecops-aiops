# Restauration du LABORATOIRE — refusée sans approbation humaine tracée.
if (-not (Select-String -Path reports\report.json -Pattern '"decision": "APPROUVÉE"' -Quiet)) { Write-Host "Aucune action APPROUVÉE → arrêt."; exit 1 }
$env:SIMULATE_FAILURE = "false"
docker compose up -d --force-recreate api
Remove-Item Env:SIMULATE_FAILURE
Start-Sleep -Seconds 5
Invoke-RestMethod http://localhost:8000/health
