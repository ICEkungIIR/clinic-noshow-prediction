"""FastAPI serving app.

Skeleton: /health and /metrics are live. Model loading from the MLflow registry
and /predict are added by the serving workstream.
"""

import time

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from triage import __version__

app = FastAPI(title="Urban Complaint Triage API", version=__version__)

REQUESTS = Counter("triage_requests_total", "HTTP requests", ["path", "method", "status"])
LATENCY = Histogram("triage_request_latency_seconds", "Request latency in seconds", ["path"])


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    path = request.url.path
    LATENCY.labels(path=path).observe(time.perf_counter() - start)
    REQUESTS.labels(path=path, method=request.method, status=response.status_code).inc()
    return response


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "model_loaded": False}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
