"""Measure bottle detection TP / FP / FN on a labeled frame set.

Labels CSV columns:
  filename,has_bottle
  frame_001.jpg,1
  empty_002.jpg,0

Place images next to the CSV (or pass --images-dir).
Run from backend/:
  python -m eval.bottle_eval --labels eval/data/bottle/labels.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vision.bottle_detector import BottleDetector


def load_labels(path: Path) -> list[tuple[str, int]]:
    rows: list[tuple[str, int]] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "filename" not in reader.fieldnames:
            raise ValueError("labels CSV must include filename,has_bottle")
        for row in reader:
            name = (row.get("filename") or "").strip()
            if not name:
                continue
            has = int(float(row["has_bottle"]))
            rows.append((name, 1 if has else 0))
    return rows


def evaluate(labels_path: Path, images_dir: Path) -> dict:
    labels = load_labels(labels_path)
    detector = BottleDetector()

    tp = fp = tn = fn = 0
    confidences: list[float] = []
    details: list[dict] = []

    for filename, gt in labels:
        image_path = images_dir / filename
        if not image_path.exists():
            raise FileNotFoundError(f"Missing image: {image_path}")
        frame = cv2.imread(str(image_path))
        if frame is None:
            raise RuntimeError(f"Could not read image: {image_path}")

        box = detector.detect(frame)
        pred = 1 if box is not None else 0
        if box is not None:
            confidences.append(box.confidence)

        if pred == 1 and gt == 1:
            tp += 1
        elif pred == 1 and gt == 0:
            fp += 1
        elif pred == 0 and gt == 0:
            tn += 1
        else:
            fn += 1

        details.append(
            {
                "filename": filename,
                "ground_truth": gt,
                "predicted": pred,
                "confidence": None if box is None else round(box.confidence, 4),
            }
        )

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    conf_sorted = sorted(confidences)

    def _pct(vals: list[float], q: float) -> float | None:
        if not vals:
            return None
        idx = int(round(q * (len(vals) - 1)))
        return round(vals[idx], 4)

    return {
        "n": len(labels),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "confidence_median": _pct(conf_sorted, 0.5),
        "confidence_p25": _pct(conf_sorted, 0.25),
        "confidence_p75": _pct(conf_sorted, 0.75),
        "details": details,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Bottle detection TP/FP/FN eval")
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=None,
        help="Defaults to the labels CSV directory",
    )
    parser.add_argument("--out", type=Path, default=None, help="Write JSON report")
    args = parser.parse_args()

    images_dir = args.images_dir or args.labels.parent
    report = evaluate(args.labels, images_dir)
    printable = {k: v for k, v in report.items() if k != "details"}
    print(json.dumps(printable, indent=2))

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
