# D25 — Plan de restauration Orders API 2.4.7 (INC-2026-1042)

**Prérequis absolu :** décision humaine tracée dans `reports/report.json` (champ `approvals`, décision `APPROUVÉE`, nom de l'approbateur, horodatage). L'outil AIOps n'exécute rien. Aucune action sur la base de données.

## 1. Avant d'agir : lever le doute (10 min max, lecture seule)

Comparer la configuration d'accès base entre 2.4.6 et 2.4.7 (`git diff v2.4.6..v2.4.7 -- app/ docker-compose.yml`). Vérifier si d'autres services utilisant la même base sont dégradés. Si la base est elle-même en panne, **le rollback ne servira à rien** : escalade à l'équipe base de données et communication client.

## 2. Analyse de risque du rollback

| Risque | Probabilité | Mitigation |
|---|---|---|
| Rollback inefficace (cause = base, pas la release) | Moyenne | Lever le doute (étape 1) ; critère d'arrêt à 5 min |
| Perte des correctifs de la 2.4.7 | Certaine | Acceptable temporairement ; ticket de reprise |
| Incompatibilité de schéma (migration 2.4.7 déjà appliquée) | À vérifier | Vérifier qu'aucune migration n'est livrée avec la 2.4.7 ; sinon **pas de rollback applicatif sans DBA** |
| Coupure pendant la bascule | Faible | Bascule progressive (canary / rolling) en production |

## 3. Exécution (laboratoire)

```bash
# Lab : la « 2.4.6 saine » est simulée par SIMULATE_FAILURE=false
./scripts/restore.sh            # Windows : .\scripts\restore.ps1
# En production (illustratif) : redéployer le tag techcorp-api:2.4.6 via le pipeline,
# ou git revert du merge 2.4.7 puis pipeline normal (traçabilité complète).
```

## 4. Validation (critères de sortie)

Le service est considéré restauré si, pendant **10 minutes consécutives** : taux d'erreur 5xx < 1 %, p95 /orders < 300 ms, `up = 1`, alertes ElevatedHTTP500 et HighHTTP500Ratio résolues, et `python -m aiops.detector` renvoie `OK`. Test fonctionnel : `curl http://localhost:8000/orders` → 200.

**Critère d'arrêt / retour arrière du rollback :** si après 5 min le taux d'erreur ne baisse pas, on stoppe et on escalade (la cause n'est pas la release).

## 5. Observabilité post-changement

Surveiller le tableau de bord Grafana pendant 30 min (annotation de version visible) ; garder l'alerte active ; ajouter, comme action durable, une **sonde readiness qui teste la base** (aujourd'hui `/health` ne teste que le processus, ce qui explique `up = 1` pendant l'incident) et des métriques de pool de connexions (`db_pool_in_use`, `db_connect_errors_total`).

## 6. Post-mortem (sans recherche de coupable, sous 5 jours ouvrés)

Chronologie détaillée ; impact (durée, % de requêtes en erreur, clients touchés) ; cause racine confirmée par des preuves ; ce qui a bien marché (détection en 2 min, rapport < 15 min) ; ce qui a manqué (pas de métriques base, pas de canary) ; actions correctives avec responsable et échéance : déploiement canary avec rollback automatique sur SLO, readiness probe DB, test d'intégration base dans la CI, métriques de pool.
