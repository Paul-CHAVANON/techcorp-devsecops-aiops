#!/usr/bin/env bash
# A4 — Pipeline VERT. Un simple « git rm » ne suffit PAS : Gitleaks scanne l'historique.
# On réécrit donc la branche (et pour un vrai secret : révocation + rotation immédiates).
set -euo pipefail
git switch test/secret-leak-demo
git fetch origin main
git reset --hard origin/main
git commit --allow-empty -m "test(A4): secret retiré de l'historique de la branche"
git push --force-with-lease
echo "→ La PR doit maintenant être VERTE."
