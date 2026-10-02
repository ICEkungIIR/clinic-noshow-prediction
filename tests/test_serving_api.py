"""API tests: /predict, /predict_batch, /reload, /health with an injected test model."""

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from noshow.serving import app as app_module

client = TestClient(app_module.app)  # no `with`: lifespan (MLflow loading) is not started


@pytest.fixture
def loaded(bundle, monkeypatch):
    monkeypatch.setattr(app_module.holder, "bundle", bundle)
    monkeypatch.setattr(app_module.holder, "last_error", None)
    return bundle


@pytest.fixture
def empty(monkeypatch):
    monkeypatch.setattr(app_module.holder, "bundle", None)
    monkeypatch.setattr(app_module.holder, "last_error", None)


def test_predict_ok(loaded, valid):
    resp = client.post("/predict", json=valid)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"PatientId", "noshow_score", "alert", "threshold", "model_version"}
    assert body["model_version"] == "test"
    assert body["alert"] == (body["noshow_score"] >= body["threshold"])


def test_api_matches_local_pipeline(loaded, valid, fitted_pipeline):
    local = fitted_pipeline.predict_proba(pd.DataFrame([valid]))[0, 1]
    served = client.post("/predict", json=valid).json()["noshow_score"]
    assert served == pytest.approx(local, abs=1e-6)


@pytest.mark.parametrize(
    "change", [{"Gender": "X"}, {"Age": "old"}, {"SMS_received": 3}, {"No-show": "Yes"}]
)
def test_predict_bad_schema_is_422(loaded, valid, change):
    assert client.post("/predict", json={**valid, **change}).status_code == 422


def test_predict_batch(loaded, valid):
    rows = [valid, {**valid, "PatientId": 2002.0, "Gender": "M", "Age": 20}]
    resp = client.post("/predict_batch", json={"appointments": rows})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["predictions"]) == 2
    assert body["n_alerts"] == sum(p["alert"] for p in body["predictions"])


def test_predict_batch_limits(loaded, valid):
    assert client.post("/predict_batch", json={"appointments": []}).status_code == 422
    too_many = {"appointments": [valid] * 1001}
    assert client.post("/predict_batch", json=too_many).status_code == 422


def test_predict_without_model_is_503(empty, valid):
    resp = client.post("/predict", json=valid)
    assert resp.status_code == 503
    assert client.get("/health").json()["model_loaded"] is False


def test_health_reports_model(loaded):
    body = client.get("/health").json()
    assert body["model_loaded"] is True
    assert body["model_version"] == "test"
    assert body["threshold"] == 0.5


def test_reload_swaps_model(loaded, monkeypatch):
    new = type(loaded)(loaded.model, threshold=0.4, version="2", uri="models:/clinic-noshow/2")
    monkeypatch.setattr(app_module.holder, "_loader", lambda: new)
    body = client.post("/reload").json()
    assert body == {"previous_version": "test", "model_version": "2"}
    assert client.get("/health").json()["threshold"] == 0.4


def test_metrics_count_predictions(loaded, valid):
    client.post("/predict", json=valid)
    text = client.get("/metrics").text
    assert "noshow_predictions_total" in text
    assert "noshow_prediction_score" in text
    info = next(line for line in text.splitlines() if line.startswith("noshow_model_info{"))
    assert 'version="test"' in info and 'threshold="0.5"' in info
