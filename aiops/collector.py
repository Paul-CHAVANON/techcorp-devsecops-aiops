"""Collecte bornée des preuves : métriques, logs, contexte de changement (C1/C2).

Le collecteur est exécuté par l'humain/SRE, PAS par le LLM : le modèle ne reçoit
que du texte et n'a aucun accès au socket Docker ni au shell.
"""
from __future__ import annotations

import json
import re
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from aiops.detector import Verdict, detect, onset_ts, samples_from_fixture, samples_from_prometheus
from aiops.redact import summarize_logs
from aiops.timeutil import local_tz, now_iso

ROOT = Path(__file__).resolve().parent


def _instant(base_url: str, query: str) -> float | None:
    url = f"{base_url}/api/v1/query?{urllib.parse.urlencode({'query': query})}"
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            res = json.load(r)["data"]["result"]
        return float(res[0]["value"][1]) if res else None
    except Exception:
        return None


def docker_logs(service: str = "api", since: str = "20m", tail: int = 500) -> list[str]:
    """Lecture seule des logs, volume borné (--tail). Pas de shell=True."""
    cmd = ["docker", "compose", "logs", "--no-color", "--timestamps", "--since", since, "--tail", str(tail), service]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
        return out.stdout.splitlines()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def iso(ts: float | None) -> str | None:
    return None if ts is None else datetime.fromtimestamp(ts, tz=local_tz()).isoformat(timespec="seconds")


def parse_ts(value: str | None) -> float | None:
    if not value:
        return None
    v = value.replace("Z", "+00:00")
    if "." in v:  # Docker : nanosecondes → microsecondes
        head, tail = v.split(".", 1)
        digits = re.match(r"\d*", tail).group()  # chiffres de la fraction seulement, pas ceux du fuseau
        v = f"{head}.{digits[:6]}{tail[len(digits):]}"
    try:
        return datetime.fromisoformat(v).timestamp()
    except ValueError:
        return None


def correlate_with_change(first_error_ts: float | None, deploy_ts: float, release: str,
                          deploy_source: str, error_source: str) -> dict:
    """Corrélation TEMPORELLE uniquement — jamais présentée comme une causalité."""
    base = {"deployed_at": iso(deploy_ts), "deployed_release": release, "deploy_source": deploy_source,
            "first_error_at": iso(first_error_ts), "first_error_source": error_source}
    if first_error_ts is None:
        return {**base, "delta_seconds": None, "statement": "Aucune erreur 500 observée."}
    delta = first_error_ts - deploy_ts
    if 0 <= delta <= 900:
        st = (f"Les premières erreurs apparaissent {delta:.0f} s (~{delta/60:.0f} min) après le déploiement "
              f"{release}. Corrélation temporelle compatible avec un lien, mais NON démonstrative d'une causalité.")
    elif delta < 0:
        st = "Les erreurs précèdent le déploiement : la release n'est probablement pas l'origine."
    else:
        st = "Plus de 15 min entre déploiement et erreurs : lien avec le changement peu probable."
    return {**base, "delta_seconds": round(delta), "statement": st}


def collect(prometheus: str | None = None, fixture: str | None = None, logs_file: str | None = None,
            change_file: str | None = None, window: int = 300) -> dict:
    change = json.loads(Path(change_file or ROOT / "change_context.json").read_text(encoding="utf-8"))

    if fixture:
        data = json.loads(Path(fixture).read_text(encoding="utf-8"))
        samples = samples_from_fixture(fixture)
        verdict: Verdict = detect(samples, window_seconds=window, now=data.get("now"))
        latency, up, other = data.get("latency_p95_seconds", {}), data.get("target_up"), None
        source = f"fixture:{fixture}"
        detected_at = iso(data.get("now"))
    else:
        samples = samples_from_prometheus(prometheus)
        verdict = detect(samples, window_seconds=window)
        latency = {"during": _instant(prometheus, 'histogram_quantile(0.95, sum by (le) (rate(techcorp_request_duration_seconds_bucket{job="techcorp-api",path="/orders"}[5m])))')}
        up = _instant(prometheus, 'up{job="techcorp-api"}')
        other = _instant(prometheus, 'sum(rate(techcorp_http_requests_total{job="techcorp-api",path!="/orders",status="500"}[5m]))')
        source = f"prometheus:{prometheus}"
        detected_at = now_iso()

    if logs_file:
        log_lines = Path(logs_file).read_text(encoding="utf-8").splitlines()
        source += f" + logs:{logs_file}"
    else:
        log_lines = docker_logs()
        source += " + docker compose logs (lecture seule, --tail borné)"
    logs = summarize_logs(log_lines)
    if not logs["deploy_events"] and not logs_file:
        # Le --tail borné perd vite l'événement de démarrage : relecture ciblée, seules les
        # lignes de déploiement sont conservées (le volume transmis reste borné).
        deploy_lines = [line for line in docker_logs(since="2h", tail=20000) if "event=deploy_success" in line]
        logs["deploy_events"] = summarize_logs(deploy_lines)["deploy_events"]

    # Heure du changement : événement de déploiement dans les logs, sinon contexte déclaré
    dep = next((d for d in reversed(logs["deploy_events"]) if parse_ts(d["ts"])), None)
    if dep:
        deploy_ts, release, dsrc = parse_ts(dep["ts"]), dep["release"] or change["deployed_version"], "logs (event=deploy_success)"
    else:
        deploy_ts, release, dsrc = parse_ts(change["deployed_at"]), change["deployed_version"], "aiops/change_context.json"
    # Première erreur : horodatage précis des logs, sinon début d'épisode des métriques (±1 pas)
    err_ts = [parse_ts(ts) for k, ts in logs["first_seen"].items() if k.startswith("ERROR") and parse_ts(ts)]
    if err_ts:
        first_err, esrc = min(err_ts), "logs"
    else:
        first_err, esrc = onset_ts(samples), "métriques Prometheus (±1 min)"

    return {
        "collected_at": now_iso(),
        "detected_at": detected_at,
        "source": source,
        "detection": verdict.to_dict(),
        "metrics": {"target_up": up, "error_rate_window": verdict.current_error_rate,
                    "latency_p95_seconds": latency, "other_routes_500_per_s": other},
        "logs": logs,
        "change": change,
        "correlation": correlate_with_change(first_err, deploy_ts, release, dsrc, esrc),
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--prometheus", default="http://localhost:9090")
    p.add_argument("--fixture")
    p.add_argument("--logs-file")
    a = p.parse_args()
    print(json.dumps(collect(None if a.fixture else a.prometheus, a.fixture, a.logs_file), indent=2, ensure_ascii=False, default=str))
