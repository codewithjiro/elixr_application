"""Combine evaluation report JSON files into Chapter 4 summary tables (CSV).

Example:
  python -m eval.export_results \\
    --bottle eval/reports/bottle.json \\
    --agreement eval/reports/agreement.json \\
    --perf eval/reports/perf.json \\
    --out-dir eval/reports/chapter4
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def _load(path: Path | None) -> dict | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_bottle_table(report: dict, out: Path) -> None:
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "n",
                "true_positive",
                "false_positive",
                "false_negative",
                "true_negative",
                "precision",
                "recall",
                "confidence_median",
            ]
        )
        w.writerow(
            [
                report.get("n"),
                report.get("true_positive"),
                report.get("false_positive"),
                report.get("false_negative"),
                report.get("true_negative"),
                report.get("precision"),
                report.get("recall"),
                report.get("confidence_median"),
            ]
        )


def write_agreement_tables(report: dict, out_dir: Path) -> None:
    overall = out_dir / "expert_agreement_overall.csv"
    with overall.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["n", "exact_matches", "agreement", "cohen_kappa"])
        w.writerow(
            [
                report.get("n"),
                report.get("exact_matches"),
                report.get("agreement"),
                report.get("cohen_kappa"),
            ]
        )

    per = out_dir / "expert_agreement_per_movement.csv"
    with per.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["movement_id", "n", "agreement", "cohen_kappa"])
        for mid, row in (report.get("per_movement") or {}).items():
            w.writerow([mid, row.get("n"), row.get("agreement"), row.get("cohen_kappa")])


def write_perf_table(report: dict, out: Path) -> None:
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "avg_fps",
                "min_fps",
                "median_latency_ms",
                "p95_latency_ms",
                "frames",
                "duration_seconds",
            ]
        )
        w.writerow(
            [
                report.get("avg_fps"),
                report.get("min_fps"),
                report.get("median_latency_ms"),
                report.get("p95_latency_ms"),
                report.get("frames"),
                report.get("duration_seconds"),
            ]
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Chapter 4 CSV tables")
    parser.add_argument("--bottle", type=Path, default=None)
    parser.add_argument("--agreement", type=Path, default=None)
    parser.add_argument("--perf", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    bottle = _load(args.bottle)
    if bottle:
        path = args.out_dir / "bottle_detection.csv"
        write_bottle_table(bottle, path)
        written.append(str(path))

    agreement = _load(args.agreement)
    if agreement:
        write_agreement_tables(agreement, args.out_dir)
        written.append(str(args.out_dir / "expert_agreement_overall.csv"))
        written.append(str(args.out_dir / "expert_agreement_per_movement.csv"))

    perf = _load(args.perf)
    if perf:
        path = args.out_dir / "performance.csv"
        write_perf_table(perf, path)
        written.append(str(path))

    if not written:
        print("No input reports found; nothing written.")
        return 1

    print("Wrote:")
    for p in written:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
