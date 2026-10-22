"""Fuseau des rapports : UTC par défaut (comme docs/fake_incident.log), configurable via REPORT_TZ."""
import os
from datetime import datetime, timezone, tzinfo


def local_tz() -> tzinfo:
    name = os.getenv("REPORT_TZ", "UTC")
    if name.upper() == "UTC":
        return timezone.utc
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:  # Windows sans le paquet tzdata
        return timezone.utc


def now_iso() -> str:
    return datetime.now(local_tz()).isoformat(timespec="seconds")
