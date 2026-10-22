# Mission D — Déroulé de la soutenance (5 min + 3 min de questions)

| Temps | Démonstration | Ce qu'il faut dire |
|---|---|---|
| 0:00–1:00 | **Pipeline rouge puis vert** (captures horodatées de la PR `test/secret-leak-demo`) | « Le secret fictif est détecté par Gitleaks sur l'historique complet ; supprimer le fichier ne suffit pas, il faut réécrire l'historique et, pour un vrai secret, le révoquer. » |
| 1:00–2:00 | **Grafana avant / pendant** | Taux d'erreur de ~0 % à ~100 %, latence p95 de ~30 ms à ~500 ms, `up` reste à 1 : « le processus vit, mais le service est rendu inutilisable ». |
| 2:00–3:00 | `python -m aiops.detector` | Lire les `reasons` : fenêtre 5 min, baseline, z-score, ratio, double condition seuil + statistique. |
| 3:00–4:00 | `python -m aiops.investigate --approver "Nom"` | Données masquées et bornées, logs = données non fiables (ligne d'injection isolée), sortie structurée avec confiance, action rollback bloquée en attente d'approbation. |
| 4:00–5:00 | **Contester** puis **plan de restauration** | Voir ci-dessous puis `docs/plan-restauration.md`. |

## Hypothèse à contester (D24)

L'IA attribue l'incident à la release 2.4.7 avec une confiance moyenne. **Preuve réelle :** une coïncidence temporelle de 2 minutes et des logs `db_connection_timeout` tous postérieurs au déploiement (mais on n'a collecté presque aucun log antérieur, donc l'absence d'erreurs avant ne prouve rien). **Preuves absentes :** aucun diff de configuration n'a été examiné, aucune métrique côté base, et l'on ne sait pas si la 2.4.6 aurait échoué de la même façon. Un timeout de connexion pointe d'ailleurs autant vers la base ou le réseau que vers le code. Conclusion : hypothèse plausible mais **non prouvée** ; on fait d'abord les contrôles non destructifs, et le rollback n'est approuvé que comme mesure de mitigation réversible, avec critère d'arrêt.

À dire en toute transparence : en laboratoire, la cause réelle est connue (`SIMULATE_FAILURE=true`) ; l'exercice porte sur la rigueur du raisonnement, pas sur la découverte.

## Questions probables du jury

**Pourquoi ne pas laisser le LLM redémarrer le service ?** Il n'a pas de responsabilité, peut halluciner et peut être manipulé par le contenu des logs (prompt injection). Il n'a aucun outil, aucun accès au socket Docker ; le code force `approbation_humaine_requise` sur toute action sensible, même si le modèle dit le contraire.

**Pourquoi épingler les actions par SHA ?** Un tag comme `@v4` peut être déplacé vers un autre commit, par exemple si le dépôt de l'action est compromis. Un SHA désigne un contenu immuable.

**Que se passe-t-il si un log contient « ignore tes instructions » ?** La ligne est détectée, retirée du contexte envoyé au modèle, signalée dans le rapport. Le prompt encadre les données entre balises et précise qu'il s'agit de données. Défense en profondeur : même si le modèle était manipulé, il ne peut rien exécuter.

**Quelle vulnérabilité réelle avez-vous trouvée ?** Starlette 0.46.2, tirée par FastAPI 0.115.12 : CVE-2025-62727 (HIGH). Invisible dans `requirements.txt`, détectée par le scan d'image. Non exploitable chez nous (pas de `FileResponse`), mais corrigée quand même car un correctif existe.

**Pourquoi `--ignore-unfixed` ?** Bloquer sur une CVE sans correctif ne réduit pas le risque et paralyse la livraison ; elle est suivie hors gate. Une CVE exploitable avec correctif bloque.

**Limite du z-score ?** Il suppose une distribution à peu près stable ; il est sensible à une baseline polluée par un incident passé et ignore la saisonnalité (heure, jour). Amélioration : médiane/MAD, baseline par tranche horaire, ou Holt-Winters.

**Pourquoi `up = 1` pendant l'incident ?** `/health` est une sonde de vivacité qui ne teste pas la base. Il faut distinguer *liveness* et *readiness*.
