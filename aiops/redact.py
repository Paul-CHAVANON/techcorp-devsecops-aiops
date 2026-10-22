"""Masquage des données sensibles et bornage des logs avant envoi au LLM (C2)."""
from __future__ import annotations

import json
import re
from collections import Counter

PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*"), "Bearer [MASQUÉ]"),
    (re.compile(r"eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}"), "[JWT_MASQUÉ]"),
    (re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|authorization)\b(\s*[=:]\s*|\"\s*:\s*\")([^\s\",}]+)"),
     r"\1\2[MASQUÉ]"),
    (re.compile(r"(?i)(postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^:/\s]+:[^@\s]+@"), r"\1://[MASQUÉ]@"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[CLE_AWS_MASQUÉE]"),
    (re.compile(r"\bTECHCORP_FAKE_[A-Z0-9]{8,}\b"), "[SECRET_FICTIF_MASQUÉ]"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[EMAIL_MASQUÉ]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IP_MASQUÉE]"),
]


INJECTION = re.compile(
    r"(?i)(ignore (all |any )?(previous|prior|above) instructions|ignore les instructions|"
    r"system prompt|you are now|tu es maintenant|drop table|rm -rf|docker (rm|kill|exec)|curl .*\|\s*sh)"
)


def redact(text: str) -> str:
    for pattern, repl in PATTERNS:
        text = pattern.sub(repl, text)
    return text


LINE = re.compile(
    r"^(?:(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+)?"
    r"(?P<level>DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL):?\s+(?P<msg>.*)$"
)
DEPLOY = re.compile(r"event=deploy_success")
RELEASE = re.compile(r"release=(?P<release>[\w.\-]+)")


def parse_line(raw: str) -> dict | None:
    """Accepte : log brut (docs/fake_incident.log), sortie `docker compose logs
    --timestamps` (préfixe « api-1  | »), ou JSON. Retourne {ts, level, msg}."""
    line = raw.strip()
    if not line:
        return None
    if " | " in line[:40]:
        line = line.split(" | ", 1)[1].strip()
    if line.startswith("{"):
        try:
            o = json.loads(line)
            return {"ts": o.get("ts"), "level": str(o.get("level", "INFO")).upper(), "msg": str(o.get("msg", "")), "raw": line}
        except json.JSONDecodeError:
            pass
    m = LINE.match(line)
    if m:
        lvl = m["level"].replace("WARNING", "WARN")
        return {"ts": m["ts"], "level": lvl, "msg": m["msg"].strip(), "raw": line}
    # Ligne horodatée par Docker mais sans niveau reconnu (ex. access log uvicorn)
    return {"ts": None, "level": "INFO", "msg": line, "raw": line}


def summarize_logs(lines: list[str], max_lines: int = 40, max_chars: int = 4000) -> dict:
    """Garde WARN/ERROR, masque, déduplique, borne le volume, extrait les
    événements de déploiement. Les logs sont des DONNÉES NON FIABLES."""
    events: Counter[str] = Counter()
    first_seen: dict[str, str | None] = {}
    examples: list[str] = []
    suspicious: list[str] = []
    deploys: list[dict] = []
    total = 0
    for raw in lines:
        rec = parse_line(raw)
        if rec is None:
            continue
        total += 1
        if DEPLOY.search(rec["msg"]):
            rel = RELEASE.search(rec["msg"])
            deploys.append({"ts": rec["ts"], "release": rel["release"] if rel else None})
            continue
        if INJECTION.search(rec["raw"]):
            suspicious.append(redact(rec["raw"])[:160])  # signalé, jamais transmis comme consigne
            continue
        if rec["level"] not in {"WARN", "ERROR", "CRITICAL"}:
            continue
        key = f"{rec['level']}:{redact(rec['msg'])[:90]}"
        events[key] += 1
        first_seen.setdefault(key, rec["ts"])
        if len(examples) < max_lines:
            examples.append(redact(rec["raw"])[:300])
    joined = "\n".join(examples)
    return {
        "lines_read": total,
        "event_counts": dict(events.most_common(10)),
        "first_seen": first_seen,
        "deploy_events": deploys[-5:],
        "examples_redacted": joined[:max_chars].splitlines(),
        "suspected_injection": suspicious[:5],
        "truncated": len(examples) >= max_lines or len(joined) > max_chars,
    }
