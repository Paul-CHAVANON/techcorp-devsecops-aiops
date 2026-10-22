#!/usr/bin/env bash
# Trafic nominal pour construire la baseline (Grafana « avant incident »). Usage : ./scripts/traffic.sh [secondes]
set -euo pipefail
DURATION="${1:-300}"; end=$((SECONDS + DURATION))
echo "Trafic nominal sur /orders pendant ${DURATION}s…"
while [ $SECONDS -lt $end ]; do curl -s -o /dev/null http://localhost:8000/orders || true; sleep 0.5; done
