"""Download the Medical Appointment No Shows dataset from Kaggle and verify SHA-256.

The SHA-256 digest is the data version logged to MLflow.
Usage: uv run python scripts/download_data.py
"""

import hashlib
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "params.yaml"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    cfg = yaml.safe_load(CONFIG.read_text())["data"]
    out = ROOT / cfg["raw_path"]
    if not out.exists():
        import kagglehub

        src_dir = Path(kagglehub.dataset_download(cfg["kaggle_dataset"]))
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src_dir / cfg["kaggle_file"], out)
    digest = sha256(out)
    print(f"{out.relative_to(ROOT)}  sha256={digest}")
    if cfg["sha256"] and digest != cfg["sha256"]:
        print("SHA-256 mismatch: data version differs from configs/params.yaml", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
