# Rapport d'incident — INC-2026-1042

**Service :** Orders API · **Généré le :** 2026-10-22T18:19:34+00:00 · **Statut :** VALIDÉ_PAR_HUMAIN  
**Analyse IA :** mode `ollama` (qwen3:14b) — *hypothèses non validées*

## 1. Résumé

Détecteur : **ANOMALY** (sévérité critical). Taux d'erreur courant 94.5% contre une baseline de 29.4% (z-score 1.44). Les premières erreurs apparaissent 81 s (~1 min) après le déploiement 2.4.7. Corrélation temporelle compatible avec un lien, mais NON démonstrative d'une causalité.

## 2. Chronologie

| Heure | Événement | Source |
|---|---|---|
| 2026-10-22T15:37:34+00:00 | Déploiement 2.4.7 | logs (event=deploy_success) |
| 2026-10-22T15:38:55+00:00 | Première erreur db_connection_timeout / HTTP 500 | logs |
| 2026-10-22T15:42:17+00:00 | Détection : ANOMALY (z-score 1.44) | aiops/detector.py |
| 2026-10-22T18:19:34+00:00 | Rapport généré | aiops/investigate.py |

## 3. Preuves collectées

**Raisonnement du détecteur :**

- Taux d'erreur courant = 94.5% (337/357) ≥ seuil 5%.
- Baseline : moyenne 29.44%, écart-type 45.27% sur 55 pas → z-score = 1.4 (seuil 3.0).
- Ratio courant/baseline = 3.2 (seuil 3.0).
- Première erreur 500 de la fenêtre vers 15:38:17 UTC (±1 pas).
- Verdict : ANOMALIE (seuil dépassé ET écart significatif à l'historique).

**Logs (masqués, bornés) — comptage par événement :**

- `ERROR:order_processing_failed db_connection_timeout route=/orders release=2.4.7 event=INC-2026-1` × 222

Lignes lues : 500 · tronqué : True

## 4. Analyse IA (hypothèses, non validées)

**Symptômes :**

- Taux d'erreur courant de 94.5% (337/357) dépassant le seuil de 5%.
- Z-score de 1.44 indiquant un écart significatif par rapport à la baseline.
- Présence d'erreurs répétées liées à des timeouts de connexion à la base de données (db_connection_timeout) sur la route /orders.
- Déploiement de la version 2.4.7 de l'API orders-api à 15:37:34 UTC, suivi de premières erreurs à 15:38:55 UTC.

| Hypothèse | Confiance | Preuves | Preuves manquantes |
|---|---|---|---|
| Le déploiement de la version 2.4.7 a introduit un problème de connexion à la base de données. | 75% | Les premières erreurs apparaissent 81 secondes après le déploiement de la version 2.4.7.<br>Les logs montrent des erreurs répétées liées à des timeouts de connexion à la base de données après le déploiement. | Aucun diff détaillé entre les versions 2.4.6 et 2.4.7 n'est disponible pour identifier les changements potentiels.<br>Aucune métrique de latence ou de performance de la base de données n'est fournie pour confirmer un problème côté base de données. |
| Le problème est lié à une dégradation de la base de données ou à une surcharge. | 50% | Les erreurs sont liées à des timeouts de connexion à la base de données. | Aucune métrique de charge ou de latence de la base de données n'est disponible.<br>Aucune information sur l'état des serveurs de base de données n'est fournie. |

**Contrôles non destructifs recommandés :**

1. Vérifier les métriques de latence et de charge de la base de données.
2. Consulter le diff détaillé entre les versions 2.4.6 et 2.4.7 pour identifier les changements potentiels.
3. Analyser les logs de la base de données pour détecter des erreurs ou des déconnexions.
4. Vérifier les configurations de connexion à la base de données dans la version 2.4.7.

**Limites :**

- Les données fournies ne permettent pas de confirmer avec certitude la cause exacte de l'incident.
- Aucune information sur l'état de la base de données ou les configurations de connexion n'est disponible.
- Aucun diff détaillé entre les versions n'est fourni, limitant l'analyse des changements potentiels.

## 5. Remédiation proposée et validation humaine

| # | Action | Risque | Approbation requise | Décision | Approbateur |
|---|---|---|---|---|---|
| 1 | Rollback vers la version 2.4.6 si les logs indiquent un déploiement réussi de la version 2.4.7. | Possibilité de perte de fonctionnalités introduites dans la version 2.4.7. | oui | APPROUVÉE | Paul Chavanon |
| 2 | Analyser le diff entre les versions 2.4.6 et 2.4.7 pour identifier les changements potentiels. | Aucun risque immédiat, mais nécessite un temps d'analyse. | non | NON_REQUISE | — |
| 3 | Vérifier les métriques de la base de données pour confirmer un problème de performance ou de charge. | Aucun risque immédiat, mais nécessite un accès aux métriques de la base de données. | non | NON_REQUISE | — |

> Aucune action n'a été exécutée par l'outil. Toute action approuvée est réalisée manuellement selon `docs/plan-restauration.md`.

## 6. Contestation (revue SRE)

L'hypothèse principale repose surtout sur une **coïncidence temporelle** avec le déploiement. Tant que le diff 2.4.6..2.4.7 et les métriques côté base n'ont pas été examinés, elle reste insuffisamment prouvée : un rollback pourrait être inefficace si la base est en cause.
