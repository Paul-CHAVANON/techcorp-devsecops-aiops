"""Orchestrateur d'investigation (C1→C5) : collecte → analyse LLM → validation
humaine → reports/report.json + reports/incident-report.md.

Aucune action corrective n'est exécutée par ce script : il enregistre seulement
la décision (APPROUVÉE / REFUSÉE / EN ATTENTE) d'un humain identifié.

Exemples :
  python -m aiops.investigate --approver "Nom SRE"          # Prometheus + docker compose logs
  python -m aiops.investigate --fixture aiops/fixtures/incident_metrics.json \
      --logs-file aiops/fixtures/incident.log --llm simulated --no-input
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from aiops.collector import collect
from aiops.llm_client import analyse
from aiops.timeutil import now_iso


def request_approvals(actions: list[dict], approver: str | None, interactive: bool,
                      approve: set[int] = frozenset(), refuse: set[int] = frozenset()) -> list[dict]:
    decisions = []
    for i, a in enumerate(actions, 1):
        if not a.get("approbation_humaine_requise"):
            decisions.append({"id": i, "action": a["action"], "decision": "NON_REQUISE"})
            continue
        decision = "EN_ATTENTE"
        if approver and i in approve:
            decision = "APPROUVÉE"
        elif approver and i in refuse:
            decision = "REFUSÉE"
        elif interactive and approver:
            print(f"\n[APPROBATION REQUISE] Action #{i} : {a['action']}\n  Risque : {a.get('risque')}")
            ans = input(f"  Tapez exactement 'APPROUVE {i}' pour approuver, 'REFUSE {i}' pour refuser, Entrée pour différer : ").strip()
            decision = {f"APPROUVE {i}": "APPROUVÉE", f"REFUSE {i}": "REFUSÉE"}.get(ans, "EN_ATTENTE")
        decisions.append({"id": i, "action": a["action"], "decision": decision,
                          "approver": approver if decision != "EN_ATTENTE" else None,
                          "decided_at": now_iso() if decision != "EN_ATTENTE" else None,
                          "executed_by_tool": False,
                          "note": "L'outil n'exécute jamais l'action : exécution manuelle par le SRE selon le plan de restauration."})
    return decisions


def render_markdown(r: dict) -> str:
    d, ev, an = r["detection"], r["evidence"], r["llm"]["analysis"]
    L = [f"# Rapport d'incident — {r['incident_id']}", "",
         f"**Service :** Orders API · **Généré le :** {r['generated_at']} · **Statut :** {r['status']}  ",
         f"**Analyse IA :** mode `{r['llm']['mode']}` ({r['llm']['model']}) — *hypothèses non validées*", "",
         "## 1. Résumé", "",
         f"Détecteur : **{d['status']}** (sévérité {d['severity']}). Taux d'erreur courant "
         f"{d['current_error_rate']:.1%} contre une baseline de {(d['baseline_mean'] or 0):.1%} "
         f"(z-score {d['z_score']}). {ev['correlation']['statement']}", "",
         "## 2. Chronologie", "",
         "| Heure | Événement | Source |", "|---|---|---|",
         f"| {ev['correlation']['deployed_at']} | Déploiement {ev['correlation']['deployed_release']} | {ev['correlation']['deploy_source']} |",
         f"| {ev['correlation']['first_error_at']} | Première erreur db_connection_timeout / HTTP 500 | {ev['correlation']['first_error_source']} |",
         f"| {r['detection_at']} | Détection : {d['status']} (z-score {d['z_score']}) | aiops/detector.py |",
         f"| {r['generated_at']} | Rapport généré | aiops/investigate.py |", "",
         "## 3. Preuves collectées", "",
         "**Raisonnement du détecteur :**", ""]
    L += [f"- {x}" for x in d["reasons"]]
    L += ["", "**Logs (masqués, bornés) — comptage par événement :**", ""]
    L += [f"- `{k}` × {v}" for k, v in ev["logs"]["event_counts"].items()]
    L += ["", f"Lignes lues : {ev['logs']['lines_read']} · tronqué : {ev['logs']['truncated']}", "",
          "## 4. Analyse IA (hypothèses, non validées)", "", "**Symptômes :**", ""]
    L += [f"- {s}" for s in an["symptomes"]]
    L += ["", "| Hypothèse | Confiance | Preuves | Preuves manquantes |", "|---|---|---|---|"]
    for h in an["hypotheses"]:
        L.append(f"| {h['titre']} | {h['confiance']:.0%} | {'<br>'.join(h.get('preuves', []))} | "
                 f"{'<br>'.join(h.get('preuves_manquantes', []))} |")
    L += ["", "**Contrôles non destructifs recommandés :**", ""]
    L += [f"{i}. {c}" for i, c in enumerate(an["controles_non_destructifs"], 1)]
    L += ["", "**Limites :**", ""] + [f"- {x}" for x in an["limites"]]
    if ev["logs"].get("suspected_injection"):
        L += ["", "**⚠ Contenu de logs ressemblant à des instructions (traité comme donnée, jamais exécuté) :**", ""]
        L += [f"- `{x}`" for x in ev["logs"]["suspected_injection"]]
    if r["llm"]["validation_warnings"]:
        L += ["", "**Alertes de validation de la sortie IA :**", ""] + [f"- {w}" for w in r["llm"]["validation_warnings"]]
    L += ["", "## 5. Remédiation proposée et validation humaine", "",
          "| # | Action | Risque | Approbation requise | Décision | Approbateur |", "|---|---|---|---|---|---|"]
    for a, dec in zip(an["remediation_proposee"], r["approvals"]):
        L.append(f"| {dec['id']} | {a['action']} | {a.get('risque', '')} | "
                 f"{'oui' if a['approbation_humaine_requise'] else 'non'} | {dec['decision']} | {dec.get('approver') or '—'} |")
    L += ["", "> Aucune action n'a été exécutée par l'outil. Toute action approuvée est réalisée manuellement "
          "selon `docs/plan-restauration.md`.", "",
          "## 6. Contestation (revue SRE)", "",
          "L'hypothèse principale repose surtout sur une **coïncidence temporelle** avec le déploiement. "
          "Tant que le diff 2.4.6..2.4.7 et les métriques côté base n'ont pas été examinés, elle reste "
          "insuffisamment prouvée : un rollback pourrait être inefficace si la base est en cause.", ""]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--prometheus", default="http://localhost:9090")
    p.add_argument("--fixture", help="Séries JSON hors ligne (ignore --prometheus)")
    p.add_argument("--logs-file", help="Fichier de logs (sinon docker compose logs)")
    p.add_argument("--llm", choices=["auto", "ollama", "simulated"], default="auto")
    p.add_argument("--approver", help="Nom du SRE qui valide")
    p.add_argument("--no-input", action="store_true", help="Pas d'interaction : actions EN_ATTENTE")
    p.add_argument("--approve", type=int, action="append", default=[], help="ID d'action approuvée (exige --approver)")
    p.add_argument("--refuse", type=int, action="append", default=[], help="ID d'action refusée (exige --approver)")
    p.add_argument("--out", default="reports")
    a = p.parse_args(argv)

    evidence = collect(prometheus=None if a.fixture else a.prometheus, fixture=a.fixture, logs_file=a.logs_file)
    llm = analyse(evidence, mode=a.llm)
    approvals = request_approvals(llm["analysis"]["remediation_proposee"], a.approver,
                                  interactive=not a.no_input and sys.stdin.isatty(),
                                  approve=set(a.approve), refuse=set(a.refuse))
    status = "EN_ATTENTE_VALIDATION" if any(x["decision"] == "EN_ATTENTE" for x in approvals) else "VALIDÉ_PAR_HUMAIN"
    an = llm["analysis"]
    top = max(an["hypotheses"], key=lambda h: h["confiance"]) if an["hypotheses"] else None
    report = {
        "incident_id": "INC-2026-1042",
        "generated_at": now_iso(),
        "detection_at": evidence["detected_at"],
        "status": status,
        "detection": evidence["detection"],
        "evidence": {k: evidence[k] for k in ("source", "metrics", "logs", "change", "correlation")},
        "llm": llm,
        "approvals": approvals,
        "disclaimer": "Les conclusions de l'IA sont des hypothèses tant qu'elles n'ont pas été validées.",
        # Champs du starter (make_report), conservés pour compatibilité
        "observations": {"http_500_window": evidence["detection"]["window_errors"],
                         "logs": evidence["logs"]["event_counts"]},
        "hypothesis": top["titre"] if top else None,
        "checks_read_only": an["controles_non_destructifs"],
        "confidence": "unverified",
        "human_approval_required": True,
    }
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    (out / "incident-report.md").write_text(render_markdown(report), encoding="utf-8")
    print(f"Rapports écrits dans {out}/ (statut : {status}, mode IA : {llm['mode']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
