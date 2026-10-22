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
