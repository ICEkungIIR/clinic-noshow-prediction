from __future__ import annotations

import argparse
import json
import math
import tempfile
from pathlib import Path

import mlflow
import yaml
from mlflow import MlflowClient

ROOT = Path(__file__).resolve().parents[3]


def check_gate(tracking_uri: str) -> dict:
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_registry_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri, registry_uri=tracking_uri)

    config = yaml.safe_load((ROOT / "configs/params.yaml").read_text(encoding="utf-8"))
    limits = yaml.safe_load((ROOT / "configs/slo.yaml").read_text(encoding="utf-8"))["gate"]
    name = config["registry"]["model_name"]
    candidate = client.get_model_version_by_alias(name, "challenger")
    run = client.get_run(candidate.run_id)
    failures = []

    if run.info.status != "FINISHED":
        failures.append("Training run is not FINISHED")

    def metric(source_run, key):
        value = float(source_run.data.metrics.get(key, float("nan")))
        if not math.isfinite(value):
            raise ValueError(f"Missing or invalid metric: {key}")
        return value

    pr_auc = metric(run, "val_pr_auc")
    recall = metric(run, "val_noshow_recall")
    threshold = float(candidate.tags["threshold"])
    if not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("Invalid model threshold")
    if threshold != metric(run, "val_threshold"):
        failures.append("Model threshold differs from evaluation threshold")

    model_uri = f"models:/{name}/{candidate.version}"
    with tempfile.TemporaryDirectory() as temp:
        model_path = Path(
            mlflow.artifacts.download_artifacts(artifact_uri=model_uri, dst_path=temp)
        )
        size_mb = (
            sum(path.stat().st_size for path in model_path.rglob("*") if path.is_file()) / 1_000_000
        )

    if pr_auc < float(limits["min_pr_auc"]):
        failures.append("PR-AUC is below the minimum")
    if recall < float(limits["min_noshow_recall"]):
        failures.append("No-show recall is below the minimum")
    if size_mb > float(limits["max_model_size_mb"]):
        failures.append("Model size exceeds the maximum")

    registered_model = client.get_registered_model(name)
    champion_version = registered_model.aliases.get("champion")
    champion = (
        client.get_model_version(name, champion_version) if champion_version is not None else None
    )

    comparison = "First model: no champion to compare"
    if champion is not None and limits["must_beat_production"]:
        production_run = client.get_run(champion.run_id)
        # Conservatively require the same data and training code.
        comparable = all(
            run.data.tags.get(key) and run.data.tags.get(key) == production_run.data.tags.get(key)
            for key in ("data_sha256", "git_sha")
        )
        if not comparable:
            failures.append(
                "Re-evaluate both models on the same validation data "
                "before comparing different data or code versions"
            )
            comparison = "Comparison blocked"
        else:
            production_recall = metric(production_run, "val_noshow_recall")
            comparison = f"Champion recall: {production_recall}"
            if recall <= production_recall:
                failures.append("Recall must be higher than champion recall")

    return {
        "model_name": name,
        "version": candidate.version,
        "passed": not failures,
        "val_pr_auc": pr_auc,
        "val_noshow_recall": recall,
        "model_size_mb": round(size_mb, 4),
        "threshold": threshold,
        "comparison": comparison,
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tracking-uri", default="http://localhost:5001")
    args = parser.parse_args()
    result = check_gate(args.tracking_uri)
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
