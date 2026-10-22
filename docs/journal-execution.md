# Journal d'exécution du TP (Mac de Paul)

Heures locales (Europe/Paris). Machine : MacBook Apple Silicon (arm64), macOS 27.

## Étape 0 — Prérequis (22/10/2026, 16:00)

| Prérequis | État | Détail |
|---|---|---|
| Docker Desktop (`docker info`) | KO | Docker n'est pas installé (ni `docker`, ni `/Applications/Docker.app`) |
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
