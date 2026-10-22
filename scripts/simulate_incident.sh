#!/usr/bin/env bash
# B3 — Incident de LABORATOIRE (local uniquement). Usage : ./scripts/simulate_incident.sh [nb_appels]
set -euo pipefail
N="${1:-30}"
echo "[1/3] $(date -u +%FT%TZ) Recréation de l'API avec SIMULATE_FAILURE=true"
SIMULATE_FAILURE=true docker compose up -d --force-recreate api
sleep 5
echo "[2/3] $N appels à /orders"
for i in $(seq 1 "$N"); do
  echo "  appel $i → HTTP $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/orders)"; sleep 1
done
echo "[3/3] Attendre ~1 min (règles for:) puis : python -m aiops.detector"
