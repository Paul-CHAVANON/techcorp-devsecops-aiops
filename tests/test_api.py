from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_orders_nominal(monkeypatch):
    monkeypatch.setenv("SIMULATE_FAILURE", "false")
    r = client.get("/orders")
    assert r.status_code == 200 and r.json()["status"] == "ready"


def test_orders_panne_simulee(monkeypatch):
    monkeypatch.setenv("SIMULATE_FAILURE", "true")
    r = client.get("/orders")
    assert r.status_code == 500


def test_metrics_exposees():
    client.get("/orders")
    body = client.get("/metrics").text
    assert 'techcorp_http_requests_total{path="/orders",status="500"}' in body
    assert "techcorp_request_duration_seconds" in body and "techcorp_app_info" in body
