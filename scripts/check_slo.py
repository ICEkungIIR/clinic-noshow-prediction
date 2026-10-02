"""Compare a Locust run against configs/slo.yaml and write docs/loadtest_report.md.

    uv run python scripts/check_slo.py loadtest/results/run [--strict]

Reads <prefix>_stats.csv produced by `locust --csv <prefix>`.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_rows(prefix: str) -> dict[str, dict]:
    path = Path(f"{prefix}_stats.csv")
    with path.open(encoding="utf-8") as f:
        return {f"{r['Type']} {r['Name']}".strip(): r for r in csv.DictReader(f)}


def summarize(row: dict) -> dict:
    total = int(row["Request Count"])
    failures = int(row["Failure Count"])
    return {
        "requests": total,
        "rps": float(row["Requests/s"]),
        "p50_ms": float(row["50%"]),
        "p95_ms": float(row["95%"]),
        "p99_ms": float(row["99%"]),
        "error_rate": failures / total if total else 0.0,
    }


def _fmt(value: float, unit: str) -> str:
    return f"{value:.0f} {unit}" if unit else f"{value:.2%}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("prefix", help="the --csv prefix given to locust")
    parser.add_argument("--users", default="50")
    parser.add_argument("--duration", default="2m")
    parser.add_argument("--out", default=str(ROOT / "docs" / "loadtest_report.md"))
    parser.add_argument("--strict", action="store_true", help="exit 1 if an SLO is missed")
    args = parser.parse_args()

    slo = yaml.safe_load((ROOT / "configs" / "slo.yaml").read_text(encoding="utf-8"))
    rows = load_rows(args.prefix)

    if "POST /predict" not in rows or int(rows["Aggregated"]["Request Count"]) == 0:
        sys.exit(f"No /predict requests in {args.prefix}_stats.csv - did locust run?")

    predict = summarize(rows["POST /predict"])
    overall = summarize(rows["Aggregated"])

    checks = [
        ("p50 latency /predict", predict["p50_ms"], slo["latency_p50_ms"], "ms", "<="),
        ("p95 latency /predict", predict["p95_ms"], slo["latency_p95_ms"], "ms", "<="),
        ("error rate (all requests)", overall["error_rate"], slo["error_rate_max"], "", "<="),
        ("availability", 1 - overall["error_rate"], slo["availability_min"], "", ">="),
    ]

    lines = [
        "# Load test report (Serving)",
        "",
        f"- Date: {datetime.now():%Y-%m-%d %H:%M}",
        f"- Tool: Locust, {args.users} concurrent users, duration {args.duration}",
        "- Traffic mix: /predict 10 : /predict_batch (20 rows) 1 : /health 1",
        f"- Raw results: `{args.prefix}_stats.csv`",
        "",
        "## SLO check (targets from `configs/slo.yaml`)",
        "",
        "| SLO | Measured | Target | Result |",
        "|---|---:|---:|:---:|",
    ]
    all_ok = True
    for name, value, target, unit, op in checks:
        ok = value <= target if op == "<=" else value >= target
        all_ok &= ok
        shown, goal = _fmt(value, unit), _fmt(target, unit)
        lines.append(f"| {name} | {shown} | {op} {goal} | {'PASS' if ok else 'FAIL'} |")

    lines += [
        "",
        "## Per-endpoint latency",
        "",
        "| Endpoint | Requests | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | Error rate |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key, row in rows.items():
        s = summarize(row)
        lines.append(
            f"| {key} | {s['requests']} | {s['rps']:.1f} | {s['p50_ms']:.0f} | "
            f"{s['p95_ms']:.0f} | {s['p99_ms']:.0f} | {s['error_rate']:.2%} |"
        )
    lines += ["", f"**Overall: {'all SLOs met' if all_ok else 'SLO missed - see FAIL rows'}**", ""]

    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 1 if (args.strict and not all_ok) else 0


if __name__ == "__main__":
    sys.exit(main())
