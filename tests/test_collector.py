from datetime import datetime, timezone

from aiops.collector import parse_ts


def test_horodatage_docker_nanosecondes_garde_son_fuseau():
    # Régression : les chiffres de « +00:00 » étaient comptés dans la fraction,
    # l'heure devenait « locale » (2 h d'écart à Paris).
    attendu = datetime(2026, 10, 22, 15, 12, 52, 123456, tzinfo=timezone.utc).timestamp()
    assert parse_ts("2026-10-22T15:12:52.123456789Z") == attendu
    assert parse_ts("2026-10-22T17:12:52.123456789+02:00") == attendu
    assert parse_ts("2026-10-22T15:12:52Z") == attendu - 0.123456
