"""Détecteur de hausse d'erreurs HTTP 500 — INC-2026-1042 (mission B5).

Conserve l'API du starter (get_error_count, detect_anomaly, make_report) et
ajoute une détection explicable, fenêtrée et comparée à l'historique :

  1. FENÊTRE COURANTE = les `window_seconds` dernières secondes ;
     BASELINE = tout l'historique qui précède.
  2. Taux courant = erreurs 500 / requêtes /orders dans la fenêtre.
  3. Comparaison à la baseline :
       - seuil absolu (5 %)            → garde-fou métier ;
       - z-score (écart en σ)          → anomalie statistique ;
       - ratio courant / moyenne       → lisible pour un humain.
  4. Volume minimal (10 requêtes) avant toute conclusion.
  ANOMALY = seuil dépassé ET (z ≥ 3 OU ratio ≥ 3). Chaque étape produit une
  phrase chiffrée dans `reasons`.

Usage :
  python -m aiops.detector                       # Prometheus local (http://localhost:9090)
  python -m aiops.detector --fixture aiops/fixtures/incident_metrics.json
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime

from aiops.timeutil import local_tz

PROMETHEUS_URL = "http://localhost:9090"
PROMETHEUS = PROMETHEUS_URL + "/api/v1/query"  # compatibilité starter
QUERY = 'sum(increase(techcorp_http_requests_total{status="500"}[1m]))'
Q_REQ = 'sum(increase(techcorp_http_requests_total{job="techcorp-api",path="/orders"}[1m]))'
Q_ERR = 'sum(increase(techcorp_http_requests_total{job="techcorp-api",path="/orders",status="500"}[1m]))'
INCIDENT_ID = "INC-2026-1042"


# --- API du starter (conservée, les tests d'origine passent toujours) ---------
def get_error_count(base_url: str = PROMETHEUS_URL) -> float:
    with urllib.request.urlopen(f"{base_url}/api/v1/query?" + urllib.parse.urlencode({"query": QUERY}), timeout=5) as r:
        payload = json.load(r)
    series = payload.get("data", {}).get("result", [])
    return float(series[0]["value"][1]) if series else 0.0


def detect_anomaly(count: float, threshold: float = 3) -> bool:
    """Seuil statique historique (même logique que la règle ElevatedHTTP500).
    Insuffisant seul : ignore le volume de trafic et le comportement habituel ;
    voir detect() pour la version fondée sur une baseline."""
    return count >= threshold


def make_report(count, logs, hypothesis):
    return {"incident_id": INCIDENT_ID,
            "observations": {"http_500_last_minute": count, "logs": logs},
            "hypothesis": hypothesis, "checks_read_only": [], "confidence": "unverified",
            "human_approval_required": True}


# --- Détection fondée sur une baseline ---------------------------------------
@dataclass(frozen=True)
class Sample:
    timestamp: float  # epoch (s), fin du pas de mesure
    requests: float   # requêtes /orders pendant le pas
    errors: float     # réponses 500 pendant le pas


@dataclass
class Verdict:
    status: str                      # OK | ANOMALY | INSUFFICIENT_DATA
    severity: str                    # none | warning | critical
    current_error_rate: float
    baseline_mean: float | None
    baseline_std: float | None
    z_score: float | None
    ratio: float | None
    window_seconds: int
    window_requests: float
    window_errors: float
    first_error_ts: float | None
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        if isinstance(d["ratio"], float) and math.isinf(d["ratio"]):
            d["ratio"] = "inf"  # JSON valide
        return d


def _rate(errors: float, requests: float) -> float:
    return errors / requests if requests > 0 else 0.0


def _hhmm(ts: float) -> str:
    return datetime.fromtimestamp(ts, local_tz()).strftime("%H:%M:%S %Z")


def detect(samples: list[Sample], window_seconds: int = 300, now: float | None = None,
           min_requests: int = 10, rate_threshold: float = 0.05, z_threshold: float = 3.0,
           ratio_threshold: float = 3.0, min_std: float = 0.005) -> Verdict:
    samples = sorted(samples, key=lambda s: s.timestamp)
    if now is None:
        now = samples[-1].timestamp if samples else time.time()
    start = now - window_seconds

    window = [s for s in samples if start < s.timestamp <= now]
    baseline = [s for s in samples if s.timestamp <= start and s.requests > 0]
    w_req = sum(s.requests for s in window)
    w_err = sum(s.errors for s in window)
    current = _rate(w_err, w_req)
    first_err = next((s.timestamp for s in window if s.errors > 0), None)

    base_rates = [_rate(s.errors, s.requests) for s in baseline]
    b_mean = statistics.fmean(base_rates) if base_rates else None
    b_std = statistics.pstdev(base_rates) if len(base_rates) >= 2 else None
    common = dict(current_error_rate=round(current, 4),
                  baseline_mean=None if b_mean is None else round(b_mean, 4),
                  baseline_std=None if b_std is None else round(b_std, 4),
                  window_seconds=window_seconds, window_requests=round(w_req, 1),
                  window_errors=round(w_err, 1), first_error_ts=first_err)
    reasons: list[str] = []

    if w_req < min_requests:
        reasons.append(f"Volume insuffisant : {w_req:.0f} requêtes /orders sur {window_seconds}s "
                       f"(< {min_requests}). Aucune conclusion statistique.")
        return Verdict("INSUFFICIENT_DATA", "none", z_score=None, ratio=None, reasons=reasons, **common)

    z = ratio = None
    if b_mean is not None:
        z = (current - b_mean) / max(b_std or 0.0, min_std)  # plancher : évite σ = 0
        ratio = math.inf if b_mean == 0 and current > 0 else (current / b_mean if b_mean > 0 else 1.0)

    over = current >= rate_threshold
    reasons.append(f"Taux d'erreur courant = {current:.1%} ({w_err:.0f}/{w_req:.0f}) "
                   f"{'≥' if over else '<'} seuil {rate_threshold:.0%}.")
    if z is None:
        reasons.append("Pas d'historique exploitable : seul le seuil absolu est appliqué.")
        abnormal = over
    else:
        reasons.append(f"Baseline : moyenne {b_mean:.2%}, écart-type {b_std or 0:.2%} sur "
                       f"{len(base_rates)} pas → z-score = {z:.1f} (seuil {z_threshold}).")
        reasons.append(f"Ratio courant/baseline = {'∞ (baseline à 0 %)' if math.isinf(ratio) else f'{ratio:.1f}'} "
                       f"(seuil {ratio_threshold}).")
        abnormal = z >= z_threshold or ratio >= ratio_threshold

    if over and abnormal:
        if first_err is not None:
            reasons.append(f"Première erreur 500 de la fenêtre vers {_hhmm(first_err)} (±1 pas).")
        reasons.append("Verdict : ANOMALIE (seuil dépassé ET écart significatif à l'historique).")
        sev = "critical" if current >= 0.25 else "warning"
        return Verdict("ANOMALY", sev, z_score=_r(z), ratio=_r(ratio), reasons=reasons, **common)
    if over:
        reasons.append("Seuil dépassé mais comportement habituel au regard de l'historique : à surveiller.")
    reasons.append("Verdict : OK.")
    return Verdict("OK", "none", z_score=_r(z), ratio=_r(ratio), reasons=reasons, **common)


def onset_ts(samples: list[Sample], rate_threshold: float = 0.05) -> float | None:
    """Début de l'épisode en cours : 1er pas de la dernière suite continue au-dessus du seuil."""
    onset = None
    for s in sorted(samples, key=lambda s: s.timestamp):
        if s.requests > 0 and _rate(s.errors, s.requests) >= rate_threshold:
            onset = s.timestamp if onset is None else onset
        else:
            onset = None
    return onset


def _r(x):
    return x if x is None or math.isinf(x) else round(x, 2)


# --- Sources de données -------------------------------------------------------
def query_range(base_url: str, query: str, start: float, end: float, step: int) -> dict[float, float]:
    params = urllib.parse.urlencode({"query": query, "start": start, "end": end, "step": step})
    with urllib.request.urlopen(f"{base_url}/api/v1/query_range?{params}", timeout=10) as r:
        result = json.load(r).get("data", {}).get("result", [])
    return {float(t): float(v) for t, v in result[0]["values"]} if result else {}


def samples_from_prometheus(base_url: str = PROMETHEUS_URL, lookback: int = 3600, step: int = 60) -> list[Sample]:
    end = time.time()
    req = query_range(base_url, Q_REQ, end - lookback, end, step)
    err = query_range(base_url, Q_ERR, end - lookback, end, step)
    return [Sample(t, req[t], err.get(t, 0.0)) for t in sorted(req)]


def samples_from_fixture(path: str) -> list[Sample]:
    with open(path, encoding="utf-8") as f:
        return [Sample(**s) for s in json.load(f)["samples"]]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Détecteur de hausse d'erreurs HTTP 500")
    p.add_argument("--prometheus", default=PROMETHEUS_URL)
    p.add_argument("--fixture", help="Séries JSON hors ligne (ignore --prometheus)")
    p.add_argument("--window", type=int, default=300)
    p.add_argument("--lookback", type=int, default=3600)
    p.add_argument("--threshold", type=float, default=0.05)
    p.add_argument("--z", type=float, default=3.0)
    a = p.parse_args(argv)
    if a.fixture:
        with open(a.fixture, encoding="utf-8") as f:
            now = json.load(f).get("now")
        samples = samples_from_fixture(a.fixture)
    else:
        now, samples = None, samples_from_prometheus(a.prometheus, a.lookback)
    v = detect(samples, window_seconds=a.window, now=now, rate_threshold=a.threshold, z_threshold=a.z)
    print(json.dumps(v.to_dict(), indent=2, ensure_ascii=False))
    return 2 if v.status == "ANOMALY" else 0


if __name__ == "__main__":
    sys.exit(main())
