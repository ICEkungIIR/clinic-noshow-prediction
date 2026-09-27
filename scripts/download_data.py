"""Download the Traffy Fondue dataset and verify its SHA-256 (= data version).

Usage: uv run python scripts/download_data.py
"""

import hashlib
import sys
from pathlib import Path

import requests
import yaml

CONFIG = Path(__file__).resolve().parents[1] / "configs" / "params.yaml"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    cfg = yaml.safe_load(CONFIG.read_text())["data"]
    out = Path(cfg["raw_path"])
    if not cfg["source_url"]:
        print("configs/params.yaml: data.source_url is empty - set it first.", file=sys.stderr)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    if not out.exists():
        with requests.get(cfg["source_url"], stream=True, timeout=60) as r:
            r.raise_for_status()
            with out.open("wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
    digest = sha256(out)
    print(f"{out}  sha256={digest}")
    if cfg["sha256"] and digest != cfg["sha256"]:
        print("SHA-256 mismatch: data version differs from configs/params.yaml", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
