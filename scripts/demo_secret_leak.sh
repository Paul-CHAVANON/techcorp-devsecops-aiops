#!/usr/bin/env bash
# A4 — Pipeline ROUGE : injection volontaire d'un secret FICTIF sur une branche de test.
set -euo pipefail
git switch -c test/secret-leak-demo
mkdir -p config
# Concaténation : le marqueur complet n'apparaît jamais dans ce script
echo "PAYMENT_API_KEY=TECHCORP_FAKE_""9F3K2L8M1Q7W4E6R" > config/leak-demo.env
git add config/leak-demo.env
git commit -m "test(A4): injection volontaire d'un secret fictif"
git push -u origin test/secret-leak-demo
echo "→ Ouvrir la PR test/secret-leak-demo → main : 'Secrets (Gitleaks)' et 'Quality gate' doivent être ROUGES."
