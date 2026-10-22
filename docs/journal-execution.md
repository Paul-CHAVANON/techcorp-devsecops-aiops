# Journal d'exécution du TP (Mac de Paul)

Heures locales (Europe/Paris). Machine : MacBook Apple Silicon (arm64), macOS 27.

## Étape 0 — Prérequis (22/10/2026, 16:00)

| Prérequis | État | Détail |
|---|---|---|
| Docker Desktop (`docker info`) | KO | Docker n'est pas installé (ni `docker`, ni `/Applications/Docker.app`) → installation par Paul (droits administrateur) |
| `docker compose version` | KO | Dépend de Docker Desktop |
| git | OK | 2.54.0 (Apple Git-157) ; pas d'identité globale, configuration locale au dépôt |
| Python ≥ 3.11 | OK | `/usr/bin/python3` = 3.9.6 (trop ancien) → Python 3.12.15 installé via uv (`~/.local/bin/python3.12`) |
| GitHub CLI `gh` | KO → OK | Absent et pas de Homebrew (son installeur exige sudo) → binaire officiel `gh_2.103.0_macOS_arm64.zip` téléchargé depuis github.com/cli/cli/releases, SHA-256 vérifié avec `gh_2.103.0_checksums.txt`, copié dans `~/.local/bin` (sans sudo) |
| `gh auth status` | KO | Non authentifié → `gh auth login` à lancer par Paul |
| Ollama (facultatif) | OK | Serveur actif sur 127.0.0.1:11434, modèle `qwen3:14b` (9,3 Go) déjà présent |
| Enregistrement de l'écran | OK | `screencapture -x` produit une image 3024×1964 avec les fenêtres visibles |
| Espace disque libre ≥ 5 Go | OK | 370 Go libres |

## Étape 1 — Mise en place locale

- 16:02 — Archive `TECHCORP_TP_DevSecOps_AIOps_SOLUTION.zip` décompressée dans `~/dev/techcorp-tp` (hors iCloud).
- 16:03 — venv créé avec Python 3.12 (le Python système 3.9 ne satisfait pas le prérequis ≥ 3.11), `pip install -r requirements-dev.txt`, `python -m pytest -q` → **23 passed** (1 avertissement de dépréciation Starlette sur `httpx`, sans impact).
- Le dossier `evidence/labo-claude/` mentionné dans les consignes n'existe pas dans l'archive (seul `evidence/.gitkeep`).

## Étape 2 — GitHub et pipeline

- 16:15 — `git init -b main`, identité **locale** au dépôt (`Paul Chavanon <chavanon.5.paul@gmail.com>`), `gh` branché comme gestionnaire d'identifiants **dans le dépôt uniquement** (`credential.https://github.com.helper`), `~/.gitconfig` global non modifié. Cinq commits de la section 4 du README.
- 16:17 — `gh repo create Paul-CHAVANON/techcorp-devsecops-aiops --public --push` → https://github.com/Paul-CHAVANON/techcorp-devsecops-aiops
- 16:17 — Protection de `main` via `gh api PUT /repos/…/branches/main/protection` : status check obligatoire **Quality gate** (branche à jour exigée), pull request obligatoire (0 relecture, un seul contributeur), règles appliquées aussi aux administrateurs (`enforce_admins`), force-push et suppression interdits.
- 16:18 — Premier workflow sur `main` (run 39794396316) **ROUGE** : Tests, Gitleaks et Trivy fs verts ; **Trivy image** en échec sur 2 vulnérabilités HIGH corrigeables dans `setuptools` fourni par `python:3.11-slim` (paquets Debian 13.7 : 0 vulnérabilité) :

  | Composant (vendored dans setuptools) | CVE | Installé | Corrigé |
  |---|---|---|---|
  | `jaraco.context` | CVE-2026-23949 (path traversal via archive tar) | 5.3.0 | 6.1.0 |
  | `wheel` | CVE-2026-24049 (exécution de code via un wheel malveillant) | 0.45.1 | 0.46.2 |

  Analyse (docs/quality-gate.md) : vulnérabilités réelles, HIGH, **correctif disponible** → la politique impose de corriger, pas d'exception. Aucun contrôle affaibli (pas de `.trivyignore`, pas de `continue-on-error`).
  Correction : `RUN pip install --no-cache-dir --upgrade setuptools==84.0.0` dans le Dockerfile. La version 84.0.0 (publiée le 08/08/2026, plus de 14 jours) a été vérifiée en inspectant son wheel : elle embarque `jaraco_context-6.1.0` et `wheel-0.46.3`. Comme `main` est protégée, la correction passe par une PR.
- 16:24 — PR #1 : 5 checks verts. Le job « Quality gate » a fini ses étapes en 3 s, mais GitHub ne l'a marqué terminé qu'environ 10 min plus tard (runners saturés). L'API `check-runs` a été utilisée pour vérifier l'état réel.
- 16:35 — PR #1 fusionnée (commit de merge `a9e3de8`), branche supprimée.
- 16:47 — CI de `main` (run 39796991552) **VERTE** : 5/5. Remarque : `gh run watch` a annoncé « success » alors que 3 jobs étaient encore en file d'attente. Le résultat a été confirmé job par job avec `gh api …/commits/main/check-runs`.

## Étape 1 (suite) — Stack Docker

- 16:29 — Docker Desktop installé par Paul. Il n'avait pas ajouté `docker` au PATH : liens créés dans `~/.local/bin` (`docker`, `docker-credential-*`). `docker compose version` → v5.6.1, Engine 29.9.2 arm64.
- 16:36 — Ports 8000, 9090 et 3000 libres. Pas de `.env.example` dans l'archive, donc pas de `.env`. `docker compose up --build -d` : les 3 images tournent nativement en **arm64**, sans adaptation propre au Mac.
- Vérifications : `/health` → `{"status":"ok","release":"2.4.7"}`, `/orders` → HTTP 200 ; Prometheus : cible `techcorp-api` **UP**, 3 règles chargées (inactives) ; Grafana 11.5.2 : dashboard « TECHCORP — Orders API (SRE) » provisionné ; `promtool test rules` → SUCCESS ; l'image contient bien setuptools 84.0.0.
- Captures : Playwright 1.64.0 + Pillow 13.0.0 dans le venv, Chromium headless téléchargé. Script versionné `scripts/capture.py` (viewport 1600×1000, locale fr-FR, fuseau Europe/Paris, attente ≥ 6 s et fin des chargements de panneaux, bandeau avec l'URL **réellement affichée** et l'heure).
- Dashboard : le panneau « Taux d'erreur HTTP 500 /orders (1 min) » affichait un axe jusqu'à 10 000 % quand la série était plate à 0 (choix automatique de Grafana). Ajout de `axisSoftMin: 0` et `axisSoftMax: 1` : l'axe va de 0 à 100 % et s'agrandit si besoin.

## Étape 3 — Démo A4 (pipeline rouge → vert)

- 16:48 — `./scripts/demo_secret_leak.sh` → commit `5bc8afb` (marqueur fictif `TECHCORP_FAKE_…` dans `config/leak-demo.env`), PR #2.
- 16:54 — Checks : **Secrets (Gitleaks) ROUGE** (règle `techcorp-fake-secret`, 1 fuite sur 8 commits, secret masqué par `--redact`), **Quality gate ROUGE**, les 3 autres verts → `evidence/A4-pr-rouge.png`, `A4-pr-rouge-gitleaks.png`, `A4-pr-checks-rouge.txt`, `A4-gitleaks-log.txt`.
- 16:56 — `./scripts/demo_secret_fix.sh` : branche réinitialisée sur `origin/main` + commit vide `21de2e9`, `push --force-with-lease`. Le commit fautif n'est plus dans l'historique de la branche.
- 17:05 — 5 checks **VERTS** → `evidence/A4-pr-vert.png`, `A4-pr-checks-vert.txt`. PR #2 fermée **sans fusion**, branche distante `test/secret-leak-demo` supprimée.

## Étape 4 — Observabilité et incident

- 16:38 — Trafic nominal (`scripts/traffic.sh`). Écart assumé par rapport à `traffic.sh 420` : avec 420 s, le trafic se serait arrêté 1 min après le début de l'incident. Or `HighHTTP500Ratio` exige plus de 0,1 req/s pendant 1 min, et la capture « APRÈS » a besoin de trafic. Le script a donc été lancé pour une durée longue, puis arrêté à la fin de l'étape.
- 16:56 — Captures AVANT (après 18 min de trafic) : `B2-grafana-avant.png`, `B1-prometheus-targets.png`, `B4-alertes-avant.png`.
- 17:06:01 — `./scripts/simulate_incident.sh 30` (trafic toujours actif) : 30/30 appels en HTTP 500. `ElevatedHTTP500` et `HighHTTP500Ratio` actives à 15:06:11 UTC, **Firing** à 17:07:12.
- 17:07 — Captures PENDANT : `B2-grafana-pendant.png`, `B4-alertes-firing.png`, `B4-graphe-taux-erreur.png` (l'axe temporel de la page Prometheus est en UTC).
- 17:08 — `python -m aiops.detector` → **ANOMALY critical**, taux 33,5 % (163/486), baseline 0 %, z = 67, code retour 2 → `evidence/B5-detector.txt`.
- Ollama : modèle installé `qwen3:14b` (aucun téléchargement). Deux défauts du client LLM, découverts et corrigés :
  1. `qwen3` est un modèle « à raisonnement » : avec `format: json` et le raisonnement actif, Ollama renvoyait `{}` (2 tokens). Le rapport sortait vide, sans action à approuver. Correction : `"think": false` dans la requête, et une réponse sans aucun champ attendu est désormais traitée comme invalide, ce qui déclenche le repli sur le mode simulé. Test `test_reponse_llm_vide_bascule_en_mode_simule`.
  2. Délai client de 120 s trop court (le modèle produit ~9 tokens/s sur ce Mac) : le premier lancement interactif avait basculé en mode simulé. Il a été interrompu (Ctrl-C) **avant toute réponse** de Paul, et aucun rapport n'a été écrit. Le délai passe à 300 s par défaut, réglable avec `OLLAMA_TIMEOUT`.
- 17:21:46 — `python -m aiops.investigate --approver "Paul Chavanon"` (mode `ollama`, `qwen3:14b`) : **Paul a tapé lui-même `APPROUVE 1`** (rollback vers 2.4.6).
- 17:22 — `./scripts/restore.sh` (autorisé par l'action APPROUVÉE). Après 3 à 8 min : `D-grafana-apres.png`, `D-alertes-apres.png`, détecteur **OK** (code retour 0) → `D-detector-apres.txt`, logs → `C-logs-extrait.txt`.
- 17:30 — En relisant le rapport, deux défauts du collecteur sont apparus, qui faussaient la chronologie :
  1. `parse_ts` comptait les chiffres de `+00:00` dans la fraction de seconde. L'horodatage Docker (`…52.123456789Z`) perdait son fuseau et était lu comme une heure locale : **2 h de décalage** à Paris (première erreur affichée à 13:12 UTC au lieu de 15:12). Invisible en CI, qui tourne en UTC. Correction et test `tests/test_collector.py`, qui échoue sur l'ancien code même en UTC.
  2. L'événement `event=deploy_success`, écrit au démarrage du conteneur, sortait de la fenêtre `--tail 500` après ~3 min de trafic. Le collecteur se rabattait alors sur `change_context.json` (10:15:01, valeur statique) et concluait « lien avec le changement peu probable ». Correction : si aucun déploiement n'est vu, relecture ciblée sur 2 h en ne gardant **que** les lignes de déploiement (le volume transmis au LLM reste borné).
  Le rapport du premier passage a été conservé hors dépôt. Décision de Paul : **rejouer l'incident** pour livrer un rapport à la chronologie juste.
- 17:32 → 17:37 — Rejeu : 5 min de trafic nominal, puis `./scripts/simulate_incident.sh 30` à 17:37:33 (30/30 en HTTP 500) ; 2 alertes **Firing** à 17:38:41.
- 17:38:41 — Détecteur : **OK** (taux 20 %, z = −0,22) alors que les alertes sont actives. La baseline d'une heure contient le premier incident (17:06–17:22), ce qui fait monter sa moyenne et son écart-type : c'est la limite « baseline polluée » du z-score. Preuve conservée : `evidence/B5-detector-rejeu-baseline-polluee.txt`.
- 17:42:07 — Détecteur : **ANOMALY** (taux 89,5 %, baseline 29 %, z = 1,33, ratio 3,07 ≥ 3) → `evidence/B5-detector-rejeu.txt`. C'est le critère du ratio qui a sauvé la détection, et non le z-score.
- 17:42 — `python -m aiops.investigate --approver "Paul Chavanon"` lancé dans le terminal de l'app (onglet « TECHCORP rejeu »). Ollama a répondu en 1 min 46 s (HTTP 200, mode `ollama`, aucun repli).
- 20:19:34 — **Paul a tapé lui-même `APPROUVE 1`** (rollback vers 2.4.6). Rapport régénéré : déploiement lu dans les logs à 15:37:34 UTC, premières erreurs vues à 15:38:55 UTC (+81 s). Limite : la vraie première erreur date de 15:37:39 ; elle est hors de la fenêtre `--tail 500`, qui ne garde que les dernières lignes.
- 20:20 — Trafic relancé, puis `./scripts/restore.sh`. Entre 18:32 et 20:20, en attendant l'approbation, il n'y avait pas de trafic : les graphes sont vides sur cette période.
- 20:28 — Preuves APRÈS : `D-grafana-apres.png` (0 % d'erreur sur 5 min, p95 ≈ 47 ms), `D-alertes-apres.png`, détecteur **OK** (code retour 0) → `D-detector-apres.txt`, `C-logs-extrait.txt` (50 dernières lignes, après restauration), `C-logs-incident-masques.txt` (logs de l'incident tels que transmis au LLM, masqués et bornés).
