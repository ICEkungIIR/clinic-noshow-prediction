from __future__ import annotations

import argparse
import json

from mlflow import MlflowClient


def rollback(tracking_uri: str) -> dict:
    client = MlflowClient(
        tracking_uri=tracking_uri,
        registry_uri=tracking_uri,
    )
    name = "clinic-noshow"
    registered = client.get_registered_model(name)
    current = registered.aliases.get("champion")
    previous = registered.aliases.get("previous_champion")

    if previous is None:
        raise ValueError("No previous champion is available for rollback")
    if current == previous:
        raise ValueError("Champion already points to the rollback version")

    target = client.get_model_version(name, previous)
    if target.status != "READY":
        raise ValueError("Previous champion is not READY")

    threshold = float(target.tags["threshold"])
    client.set_registered_model_alias(name, "champion", previous)

    return {
        "model_name": name,
        "rolled_back_from": current,
        "champion_version": previous,
        "model_uri": f"models:/{name}@champion",
        "threshold": threshold,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tracking-uri", default="http://localhost:5001")
    args = parser.parse_args()
    print(json.dumps(rollback(args.tracking_uri), indent=2))


if __name__ == "__main__":
    main()
