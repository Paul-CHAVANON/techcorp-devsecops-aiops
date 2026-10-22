#!/usr/bin/env bash
# Retour à l'état nominal du LABORATOIRE — refusé sans approbation humaine tracée dans reports/report.json.
set -euo pipefail
grep -q '"decision": "APPROUVÉE"' reports/report.json || { echo "Aucune action APPROUVÉE dans reports/report.json → arrêt."; exit 1; }
echo "$(date -u +%FT%TZ) Restauration approuvée : SIMULATE_FAILURE=false"
SIMULATE_FAILURE=false docker compose up -d --force-recreate api
sleep 5; curl -s http://localhost:8000/health; echo
