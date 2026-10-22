import json

from aiops.collector import collect
from aiops.llm_client import build_prompt, harden

FIXTURE = "aiops/fixtures/incident_metrics.json"
LOGS = "aiops/fixtures/incident.log"


def test_rollback_force_en_approbation_humaine():
    analysis = {"hypotheses": [], "remediation_proposee": [
        {"action": "Rollback vers 2.4.6", "approbation_humaine_requise": False}]}
    out, warnings = harden(analysis)
    assert out["remediation_proposee"][0]["approbation_humaine_requise"] is True
    assert warnings


def test_hypothese_sans_preuve_plafonnee():
    out, _ = harden({"hypotheses": [{"titre": "x", "confiance": 0.95, "preuves": []}]})
    assert out["hypotheses"][0]["confiance"] <= 0.3


def test_prompt_masque_et_encadre_les_donnees():
    prompt = build_prompt(collect(fixture=FIXTURE, logs_file=LOGS))
    data = prompt.rsplit("<<<DONNEES_NON_FIABLES>>>", 1)[1].rsplit("<<<FIN_DONNEES>>>", 1)[0]
    assert "client@example.com" not in data and "abcdefabcdefabcdef" not in data
    assert "IGNORE PREVIOUS" not in data          # l'injection n'atteint jamais le modèle
    corr = json.loads(data)["correlation"]
    assert corr["delta_seconds"] == 121 and corr["deploy_source"].startswith("logs")
