# TECHCORP — TP intégré DevSecOps + AIOps (INC-2026-1042)

Solution construite sur le squelette fourni : mêmes chemins, mêmes métriques (`techcorp_http_requests_total`, `techcorp_request_duration_seconds`), même règle `ElevatedHTTP500`, mêmes fonctions de départ dans `aiops/detector.py` (les tests d'origine passent toujours). Voir `SUJET_TP.md` et le PDF pour le scénario.

## 1. Lancement

macOS / Linux :

```bash
docker compose up --build -d && docker compose ps
curl http://localhost:8000/health && curl http://localhost:8000/orders
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q                      # 23 tests
```

Windows / PowerShell :

```powershell
docker compose up --build -d; docker compose ps
Invoke-RestMethod http://localhost:8000/health; Invoke-RestMethod http://localhost:8000/orders
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt; python -m pytest -q
```

Prometheus : http://localhost:9090 · Grafana : http://localhost:3000 (dashboard provisionné, lecture anonyme **uniquement en laboratoire**) · Ollama (facultatif) : `ollama pull llama3.2` ou `export OLLAMA_MODEL=<modèle de ollama list>`.

## 2. Scénario d'incident reproductible

```bash
./scripts/traffic.sh 300 &                 # baseline saine (Windows : .\scripts\traffic.ps1)
./scripts/simulate_incident.sh 30          # SIMULATE_FAILURE=true + 30 appels (Windows : .\scripts\simulate_incident.ps1)
python -m aiops.detector                   # verdict explicable (code retour 2 si anomalie)
python -m aiops.investigate --approver "Prénom Nom"   # preuves → IA → validation humaine → reports/
./scripts/restore.sh                       # refusé si aucune action APPROUVÉE dans reports/report.json
```

L'injection de panne du README d'origine (modifier `SIMULATE_FAILURE` dans `docker-compose.yml` puis `docker compose up -d --force-recreate api`) fonctionne toujours : la variable vaut `false` par défaut et peut être surchargée.

Mode hors ligne, sans Docker ni Ollama, résultat déterministe :

```bash
python -m aiops.detector --fixture aiops/fixtures/incident_metrics.json
python -m aiops.investigate --fixture aiops/fixtures/incident_metrics.json \
  --logs-file aiops/fixtures/incident.log --llm simulated --no-input
```

`--llm auto` (défaut) utilise Ollama s'il répond sur `OLLAMA_URL` (défaut `http://localhost:11434`), sinon passe en mode simulé et l'écrit dans `report.json` (`llm.mode`, `llm.fallback_reason`). Les heures sont en UTC, comme `docs/fake_incident.log` (`REPORT_TZ=Europe/Paris` pour l'heure locale).

## 3. Correspondance avec le sujet

| Exigence | Où |
|---|---|
| A1 registre de 5 risques | `docs/registre-risques.md` |
| A2 Pytest + Gitleaks + Trivy fs/image, actions épinglées | `.github/workflows/ci.yml`, `.gitleaks.toml`, `.trivyignore` |
| A3 quality gate | job `Quality gate` + `docs/quality-gate.md` |
| A4 pipeline rouge → vert | `scripts/demo_secret_leak.sh` puis `scripts/demo_secret_fix.sh` |
| A5 secrets, GITHUB_TOKEN, Kubernetes Secrets | `docs/secrets-et-permissions.md` |
| B1/B2 Prometheus + Grafana | `monitoring/`, `docs/observabilite.md` |
| B3 incident | `scripts/simulate_incident.sh` / `.ps1` |
| B4 ElevatedHTTP500 vs anomalie | `monitoring/alerts.yml`, `docs/observabilite.md` |
| B5 détecteur + tests (bonus z-score) | `aiops/detector.py`, `tests/test_detector.py` |
| C1 corrélation non causale | `aiops/collector.py` |
| C2 masquage, bornage | `aiops/redact.py` |
| C3/C4 Ollama `/api/generate`, sortie structurée | `aiops/llm_client.py` |
| C5 rapports + approbation | `aiops/investigate.py`, `reports/report.json`, `reports/incident-report.md` |
| D soutenance, restauration, post-mortem | `docs/soutenance.md`, `docs/plan-restauration.md` |
| Preuves à capturer | `docs/preuves.md` → dossier `evidence/` |

## 4. Mise sur GitHub avec des commits lisibles

```bash
git init -b main
git add app Dockerfile .dockerignore docker-compose.yml && git commit -m "feat(api): durcit l'API et met à jour les dépendances vulnérables"
git add monitoring && git commit -m "feat(obs): dashboard Grafana provisionné et règle HighHTTP500Ratio"
git add .github .gitleaks.toml .trivyignore && git commit -m "ci(sec): Gitleaks, Trivy fs/image et quality gate"
git add aiops tests pytest.ini requirements-dev.txt && git commit -m "feat(aiops): détecteur à baseline, collecte bornée, analyse Ollama"
git add . && git commit -m "docs: registre des risques, quality gate, plan de restauration, rapports"
git remote add origin <URL_DU_DEPOT> && git push -u origin main
```

Puis Settings → Branches → règle sur `main` → *Require status checks* → cocher **Quality gate**.

## 5. Sécurité

Aucun vrai secret (marqueur fictif `TECHCORP_FAKE_…` pour la démo). Services liés à `127.0.0.1`. Le LLM n'a ni outil ni accès à `/var/run/docker.sock` : il reçoit du texte et renvoie du texte. Les logs sont des données non fiables. Aucune remédiation automatique. Nettoyage : `docker compose down`.
