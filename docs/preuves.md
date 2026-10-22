# Preuves à placer dans `evidence/` avant le rendu

- `evidence/A4-pipeline-rouge.png` : PR avec « Secrets (Gitleaks) » et « Quality gate » en échec (heure visible).
- `evidence/A4-pipeline-vert.png` : même PR, tous les checks verts après nettoyage (heure visible).
- `evidence/B1-prometheus-target.png` : page Targets, `techcorp-api` UP.
- `evidence/B2-grafana-avant.png` et `evidence/B2-grafana-pendant.png`.
- `evidence/B4-alerte-firing.png` : ElevatedHTTP500 et HighHTTP500Ratio en *Firing*.
- `evidence/B5-detector.txt` : `python -m aiops.detector > evidence/B5-detector.txt`.
- `evidence/C3-ollama.txt` : sortie de `ollama list` + mode utilisé (champ `llm.mode` du rapport).
- `reports/report.json` et `reports/incident-report.md` régénérés sur VOTRE incident.
