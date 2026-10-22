from aiops.detector import detect_anomaly, make_report

def test_threshold():
    assert not detect_anomaly(2)
    assert detect_anomaly(3)

def test_approval_required():
    assert make_report(4, [], 'pending')['human_approval_required'] is True


# ---------------------------------------------------------------------------
# Tests ajoutés : détection fenêtrée, baseline, z-score, explicabilité
# ---------------------------------------------------------------------------
import math

from aiops.detector import Sample, detect, onset_ts

STEP = 60


def series(points, start=0):
    return [Sample(start + i * STEP, req, err) for i, (req, err) in enumerate(points)]


def healthy(n, req=60):
    pattern = [0, 1, 0, 0, 1]
    return [(req, pattern[i % 5]) for i in range(n)]


def test_trafic_normal_donne_ok():
    v = detect(series(healthy(40)))
    assert v.status == "OK" and v.current_error_rate < 0.05


def test_pic_de_500_detecte_et_explique():
    v = detect(series(healthy(40) + [(60, 40)] * 5))
    assert v.status == "ANOMALY" and v.severity == "critical"
    assert v.z_score > 3
    assert any("z-score" in r for r in v.reasons) and any("ANOMALIE" in r for r in v.reasons)


def test_faible_volume_pas_de_conclusion():
    v = detect(series(healthy(40) + [(1, 1), (1, 1), (0, 0), (1, 0), (0, 0)]))
    assert v.status == "INSUFFICIENT_DATA"


def test_fenetre_temporelle_ignore_un_pic_ancien():
    v = detect(series(healthy(10) + [(60, 45)] * 5 + healthy(20)))
    assert v.status == "OK"


def test_baseline_a_zero_ratio_infini():
    v = detect(series([(60, 0)] * 30 + [(60, 20)] * 5))
    assert v.status == "ANOMALY" and math.isinf(v.ratio)
    assert v.to_dict()["ratio"] == "inf"


def test_service_habituellement_bruite_reste_ok():
    v = detect(series([(100, 7 + (i % 3)) for i in range(40)]))
    assert v.status == "OK" and any("habituel" in r for r in v.reasons)


def test_seuil_statique_ignore_le_volume():
    # Limite du starter : 3 erreurs sur 3000 requêtes (0,1 %) déclenchent quand même l'alerte.
    assert detect_anomaly(3)
    v = detect(series(healthy(40, req=600) + [(600, 1), (600, 1), (600, 0), (600, 1), (600, 0)]))
    assert v.status == "OK"


def test_onset_debut_episode():
    assert onset_ts(series(healthy(10) + [(60, 40)] * 4)) == 10 * STEP
