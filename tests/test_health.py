from fastapi.testclient import TestClient

from triage.serving.app import app

client = TestClient(app)


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_metrics_exposed():
    client.get("/health")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "triage_requests_total" in resp.text
