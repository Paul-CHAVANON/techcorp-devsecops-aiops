# Mission B — Observabilité, PromQL et détection

## B1. Cible et séries dans Prometheus

http://localhost:9090/targets → `techcorp-api` doit être **UP**. Requêtes (onglet *Query*) :

| Objectif | PromQL |
|---|---|
| Disponibilité de la cible | `up{job="techcorp-api"}` |
| Requêtes 200 /s sur /orders | `sum(rate(techcorp_http_requests_total{path="/orders",status="200"}[1m]))` |
| Requêtes 500 /s sur /orders | `sum(rate(techcorp_http_requests_total{path="/orders",status="500"}[1m]))` |
| Débit par route et statut | `sum by (path, status) (rate(techcorp_http_requests_total[1m]))` |
| Taux d'erreur /orders | `sum(rate(techcorp_http_requests_total{path="/orders",status="500"}[1m])) / clamp_min(sum(rate(techcorp_http_requests_total{path="/orders"}[1m])), 1e-9)` |
| Latence p95 /orders | `histogram_quantile(0.95, sum by (le) (rate(techcorp_request_duration_seconds_bucket{path="/orders"}[1m])))` |
| Nombre de 500 sur 1 min (règle fournie) | `sum(increase(techcorp_http_requests_total{status="500"}[1m]))` |
| Release déployée | `techcorp_app_info` |

`techcorp_http_requests_total` est un **compteur** : il ne fait qu'augmenter (et repart de 0 au redémarrage). `rate()` le transforme en vitesse par seconde en gérant ces remises à zéro. La latence est un **histogramme** : il permet de calculer des percentiles, alors qu'une moyenne cache les requêtes lentes.

Amélioration apportée à l'application : les séries `status="500"` sont **pré-initialisées à 0** au démarrage. Sans cela, la série n'existe qu'à la première erreur et `increase()` sous-estime le début de l'incident.

## B2. Tableau de bord Grafana

Provisionné automatiquement : http://localhost:3000 → Dashboards → TECHCORP → **« TECHCORP — Orders API (SRE) »**. Panneaux : disponibilité (`up`), release, taux d'erreur 5 min (vert / orange 1 % / rouge 5 %), nombre de 500 sur 1 min (valeur de la règle fournie), taux d'erreur 1 min avec ligne de seuil, débit par route et statut, latence p50/p95/p99. Une annotation marque chaque redémarrage de l'API.

Captures : **avant** (après `./scripts/traffic.sh 300`) et **pendant** (après `./scripts/simulate_incident.sh`).

## B4. La règle ElevatedHTTP500 et ses limites

Règle fournie (conservée) : `sum(increase(techcorp_http_requests_total{status="500"}[1m])) >= 3` pendant 15 s. Vérification : http://localhost:9090/alerts → *Pending* puis *Firing*.

Ses défauts : c'est un **nombre absolu**, pas une proportion. 3 erreurs sur 3 requêtes (100 %) et 3 erreurs sur 30 000 requêtes (0,01 %) déclenchent la même alerte, ce qui produit des fausses alertes en pic de trafic et rate une panne totale à très faible trafic. Elle ignore aussi l'historique. La fenêtre `for: 15s` plus courte que la fenêtre d'évaluation rend l'alerte nerveuse. J'ai donc ajouté **`HighHTTP500Ratio`** : proportion de 500 sur /orders > 5 % pendant 1 min, avec un trafic minimal de 0,1 req/s.

| | Seuil d'alerte | Détection d'anomalies statistique (`aiops/detector.py`) |
|---|---|---|
| Référence | Valeur fixe choisie par un humain | Le comportement **passé** du service (baseline) |
| Question | « Est-ce au-dessus de X ? » | « Est-ce anormal **pour ce service** ? » |
| Forces | Simple, prévisible, aligné sur un SLO | S'adapte au bruit habituel, distingue un service naturellement bruité d'une vraie panne |
| Faiblesses | Ignore l'historique et souvent le volume | Besoin d'historique propre ; une baseline polluée normalise l'anormal ; saisonnalité ; plus dur à expliquer |

Les deux règles sont couvertes par des tests unitaires `promtool` (`monitoring/tests/alerts_test.yml`, exécutés en CI) : aucune alerte pendant les 10 minutes saines, les deux en *Firing* pendant l'incident.

Le test `test_seuil_statique_ignore_le_volume` démontre la limite : 3 erreurs sur 3 000 requêtes déclenchent `detect_anomaly()` (logique du starter) mais pas `detect()`.

## B5. Calcul du détecteur (à expliquer à l'oral)

1. Séries récupérées par `query_range` : requêtes et 500 sur /orders, par pas de 1 min (`increase(...[1m])`), sur 1 h.
2. **Fenêtre courante** = 5 dernières minutes ; **baseline** = les pas précédents qui ont du trafic.
3. Taux courant = Σ erreurs / Σ requêtes de la fenêtre.
4. Baseline : moyenne μ et écart-type σ des taux par minute.
5. **z = (taux courant − μ) / max(σ ; 0,5 %)**. Le plancher évite une division par zéro quand l'historique est parfaitement plat.
6. **ANOMALY** si taux ≥ 5 % **et** (z ≥ 3 **ou** ratio ≥ 3) ; **INSUFFICIENT_DATA** si moins de 10 requêtes ; sinon **OK**.
7. Chaque étape écrit une phrase chiffrée dans `reasons`. Code retour 2 en cas d'anomalie (utilisable en script).

Sur la fixture : 202 erreurs / 324 requêtes = 62,3 % ; μ = 0,16 % ; σ = 0,48 % → plancher 0,5 % → z ≈ 124 ; ratio ≈ 385 → **ANOMALY critique**.
