"""FastAPI serving app for the clinic no-show model.

Endpoints
  GET  /health         liveness + which model version is loaded
  POST /predict        score one appointment
  POST /predict_batch  score up to 1000 appointments
  POST /reload         re-read the champion from the MLflow registry (after promote/rollback)
  GET  /metrics        Prometheus metrics (latency, requests, predictions, scores)
"""

import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

from noshow import __version__
from noshow.serving.model import ModelBundle, ModelHolder
from noshow.serving.schemas import Appointment, BatchRequest, BatchResponse, Prediction

REQUESTS = Counter("noshow_requests_total", "HTTP requests", ["path", "method", "status"])
LATENCY = Histogram(
    "noshow_request_latency_seconds",
    "Request latency in seconds",
    ["path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0, 2.5),
)
PREDICTIONS = Counter("noshow_predictions_total", "Scored appointments", ["alert"])
SCORES = Histogram(
    "noshow_prediction_score",
    "Distribution of no-show scores (for drift monitoring)",
    buckets=[i / 10 for i in range(1, 10)],
)
MODEL_INFO = Gauge("noshow_model_info", "Currently loaded model", ["version", "threshold"])

holder = ModelHolder()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.getenv("MODEL_LOAD_ON_STARTUP", "1") == "1":
        holder.load_in_background()
    yield


app = FastAPI(title="Clinic No-Show Prediction API", version=__version__, lifespan=lifespan)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    path = request.url.path
    LATENCY.labels(path=path).observe(time.perf_counter() - start)
    REQUESTS.labels(path=path, method=request.method, status=response.status_code).inc()
    return response


def _require_model() -> ModelBundle:
    bundle = holder.get()
    if bundle is None:
        detail = "Model not loaded yet"
        if holder.last_error:
            detail += f" ({holder.last_error})"
        raise HTTPException(status_code=503, detail=detail)
    return bundle


def _score(bundle: ModelBundle, appointments: list[Appointment]) -> list[dict]:
    results = bundle.predict([a.to_record() for a in appointments])
    for item in results:
        PREDICTIONS.labels(alert=str(item["alert"]).lower()).inc()
        SCORES.observe(item["noshow_score"])
    return results


@app.get("/health")
def health() -> dict:
    bundle = holder.get()
    return {
        "status": "ok",
        "version": __version__,
        "model_loaded": bundle is not None,
        "model_version": bundle.version if bundle else None,
        "model_uri": bundle.uri if bundle else None,
        "threshold": bundle.threshold if bundle else None,
        "last_error": holder.last_error,
    }


@app.post("/predict", response_model=Prediction)
def predict(appointment: Appointment) -> dict:
    return _score(_require_model(), [appointment])[0]


@app.post("/predict_batch", response_model=BatchResponse)
def predict_batch(batch: BatchRequest) -> dict:
    results = _score(_require_model(), batch.appointments)
    return {"predictions": results, "n_alerts": sum(r["alert"] for r in results)}


@app.post("/reload")
def reload() -> dict:
    old = holder.get()
    new = holder.reload()
    if new is None or (new is old and holder.last_error):
        raise HTTPException(status_code=503, detail=f"Reload failed: {holder.last_error}")
    MODEL_INFO.clear()
    MODEL_INFO.labels(version=new.version, threshold=str(new.threshold)).set(1)
    return {"previous_version": old.version if old else None, "model_version": new.version}


@app.get("/metrics")
def metrics() -> Response:
    bundle = holder.get()
    if bundle is not None:
        MODEL_INFO.clear()
        MODEL_INFO.labels(version=bundle.version, threshold=str(bundle.threshold)).set(1)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
