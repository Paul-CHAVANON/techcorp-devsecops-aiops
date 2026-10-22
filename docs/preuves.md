# Preuves dans `evidence/` (captures horodatées : `scripts/capture.py`)

Synthèse commentée : [RENDU.md](RENDU.md).

- `A4-pr-rouge.png`, `A4-pr-rouge-gitleaks.png` : PR #2 avec « Secrets (Gitleaks) » et « Quality gate » en échec (heure dans le bandeau).
- `A4-pr-vert.png` : même PR, les 5 checks verts après réécriture de l'historique.
- `A4-pr-checks-rouge.txt`, `A4-pr-checks-vert.txt`, `A4-gitleaks-log.txt` : `gh pr checks` horodatés et extrait du job Gitleaks (secret masqué).
- `B1-prometheus-targets.png` : page Targets, `techcorp-api` UP.
- `B2-grafana-avant.png`, `B2-grafana-pendant.png`, `D-grafana-apres.png` : dashboard avant, pendant et après l'incident.
- `B4-alertes-avant.png`, `B4-alertes-firing.png`, `D-alertes-apres.png` : ElevatedHTTP500 et HighHTTP500Ratio inactives, puis en *Firing*, puis résolues.
- `B4-graphe-taux-erreur.png` : graphe PromQL du taux d'erreur.
- `B5-detector.txt`, `B5-detector-rejeu-baseline-polluee.txt`, `B5-detector-rejeu.txt`, `D-detector-apres.txt` : sorties de `python -m aiops.detector`, avec le code retour.
- `C3-ollama.txt` : `ollama list` et mode utilisé (champ `llm.mode` du rapport).
- `C-logs-incident-masques.txt`, `C-logs-extrait.txt` : logs transmis au LLM (masqués et bornés), et `docker compose logs --tail 50 api`.
- `reports/report.json` et `reports/incident-report.md` : régénérés sur l'incident rejoué, approuvés par Paul Chavanon.
