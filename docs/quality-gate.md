# A3 — Quality gate de la pull request

Le job **`Quality gate`** agrège les quatre contrôles. Il est configuré comme *status check obligatoire* dans la protection de la branche `main` (Settings → Branches → Require status checks → « Quality gate »). Si un seul contrôle échoue, la fusion est impossible.

## Ce qui bloque automatiquement

| Catégorie | Outil | Règle | Pourquoi |
|---|---|---|---|
| Test en échec | Pytest | tout échec | Régression fonctionnelle |
| Secret détecté | Gitleaks (historique complet) | toute détection | Un secret poussé est réputé compromis |
| Vulnérabilité **HIGH/CRITICAL avec correctif disponible** dans les dépendances | Trivy `fs` | `--severity HIGH,CRITICAL --ignore-unfixed` | Exploitable et corrigeable : aucune raison de livrer |
| Même règle sur l'image (paquets OS + Python) | Trivy `image` | idem | L'image est ce qui tourne réellement |

## Ce qui ne bloque pas (mais est tracé)

Les vulnérabilités LOW/MEDIUM et les HIGH/CRITICAL **sans correctif publié** (`--ignore-unfixed`) ne bloquent pas : bloquer sur un problème que personne ne peut corriger paralyse les livraisons sans réduire le risque. Elles sont revues chaque semaine. Les mauvaises configurations (Trivy `config`) sont informatives au début, puis deviendront bloquantes.

## Distinguer trois cas

**Vulnérabilité exploitable** : composant vulnérable présent ET chemin d'exploitation plausible (fonction appelée, service exposé). → Blocage, mise à jour de la dépendance ou de l'image de base.

**Faux positif** : l'outil se trompe (version mal détectée, paquet absent de l'image finale, secret qui est en réalité une donnée de test non sensible). → On corrige la *détection* (règle Gitleaks plus précise, empreinte ciblée), jamais en désactivant l'outil ou en excluant un dossier entier.

**Exception approuvée** : vulnérabilité réelle mais risque accepté (non exploitable dans notre contexte, correctif impossible à court terme). → Entrée dans `.trivyignore` (ou bloc `[[allowlists]]` ciblé dans `.gitleaks.toml`) avec **justification, nom de l'approbateur (RSSI/responsable sécurité) et date d'expiration**. Le fichier d'exceptions est soumis à revue de code comme le reste : un développeur ne peut pas s'auto-approuver.

## Exemple concret tiré du starter

`starlette 0.46.2` (CVE-2025-62727, HIGH) : la fonction vulnérable (`FileResponse` avec en-tête Range) n'est **pas utilisée** par Orders API, donc l'exploitabilité réelle est faible. On aurait pu demander une exception. Mais un correctif existe et la mise à jour est simple : la politique impose de **corriger**, pas d'accepter. Une exception se justifie seulement quand le correctif est impossible à court terme.

## Exceptions en vigueur

Aucune.
