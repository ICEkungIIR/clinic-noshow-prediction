"""Load the serving model (sklearn Pipeline) and its decision threshold.

Source of truth is the MLflow registry written by the registry workstream:
  models:/clinic-noshow@champion   + model-version tag `threshold`

Environment variables
  MODEL_URI            default models:/<registry.model_name>@champion
  MLFLOW_TRACKING_URI  e.g. http://mlflow:5000 inside docker compose
  MODEL_PATH           optional local MLflow model directory (offline dev / tests);
                       overrides MODEL_URI when set
  MODEL_THRESHOLD      optional override; otherwise registry tag -> params.yaml
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
PARAMS_PATH = ROOT / "configs" / "params.yaml"
RETRY_SECONDS = 15.0


def _params() -> dict:
    return yaml.safe_load(PARAMS_PATH.read_text(encoding="utf-8"))


def default_model_uri() -> str:
    return f"models:/{_params()['registry']['model_name']}@champion"


def default_threshold() -> float:
    return float(_params()["model"]["selected_threshold"])


@dataclass(frozen=True)
class ModelBundle:
    model: Any  # fitted sklearn Pipeline: features -> columns -> classifier
    threshold: float
    version: str
    uri: str

    def predict(self, records: list[dict]) -> list[dict]:
        frame = pd.DataFrame.from_records(records)
        scores = self.model.predict_proba(frame)[:, 1]
        return [
            {
                "PatientId": record["PatientId"],
                "noshow_score": round(float(score), 6),
                "alert": bool(score >= self.threshold),
                "threshold": self.threshold,
                "model_version": self.version,
            }
            for record, score in zip(records, scores, strict=True)
        ]


def _registry_info(uri: str) -> tuple[str, float | None]:
    """Return (version, threshold tag) for a models:/name@alias or models:/name/version URI."""
    from mlflow import MlflowClient

    ref = uri.removeprefix("models:/")
    client = MlflowClient()
    if "@" in ref:
        name, alias = ref.split("@", 1)
        mv = client.get_model_version_by_alias(name, alias)
    else:
        name, version = ref.rsplit("/", 1)
        mv = client.get_model_version(name, version)
    tag = mv.tags.get("threshold")
    return str(mv.version), (float(tag) if tag is not None else None)


def load_bundle() -> ModelBundle:
    import mlflow.sklearn

    local_path = os.getenv("MODEL_PATH")
    uri = local_path or os.getenv("MODEL_URI") or default_model_uri()

    model = mlflow.sklearn.load_model(uri)

    version, tag_threshold = "local", None
    if uri.startswith("models:/"):
        version, tag_threshold = _registry_info(uri)

    env_threshold = os.getenv("MODEL_THRESHOLD")
    if env_threshold is not None:
        threshold = float(env_threshold)
    elif tag_threshold is not None:
        threshold = tag_threshold
    else:
        threshold = default_threshold()
    if not 0.0 <= threshold <= 1.0:
        raise ValueError(f"threshold must be in [0, 1], got {threshold}")

    log.info("Loaded model %s (version %s, threshold %.3f)", uri, version, threshold)
    return ModelBundle(model=model, threshold=threshold, version=version, uri=uri)


class ModelHolder:
    """Holds the current model.

    Loading never happens inside a request (it would blow the latency SLO). At startup a
    background thread retries until MLflow is up and a champion exists, so `docker compose up`
    works even before the first model is registered. POST /reload swaps in a new champion
    (e.g. after promote or rollback) without restarting the container.
    """

    def __init__(self, loader=load_bundle) -> None:
        self._loader = loader
        self._lock = threading.Lock()
        self.bundle: ModelBundle | None = None
        self.last_error: str | None = None

    def get(self) -> ModelBundle | None:
        return self.bundle

    def load_in_background(self, retry_seconds: float = RETRY_SECONDS) -> threading.Thread:
        def _run() -> None:
            while self.reload() is None:
                time.sleep(retry_seconds)

        thread = threading.Thread(target=_run, name="model-loader", daemon=True)
        thread.start()
        return thread

    def reload(self) -> ModelBundle | None:
        with self._lock:
            try:
                self.bundle = self._loader()
                self.last_error = None
            except Exception as exc:  # keep serving the old model if reload fails
                self.last_error = f"{type(exc).__name__}: {exc}"
                log.warning("Model load failed: %s", self.last_error)
        return self.bundle

    def set(self, bundle: ModelBundle | None) -> None:
        self.bundle = bundle
        self.last_error = None
