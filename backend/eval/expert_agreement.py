"""Compare system checkpoint/session decisions with expert labels.

CSV columns:
  attempt_id,movement_id,system_status,expert_status

Statuses: passed | failed | not_assessed | unable_to_assess | partial

Run from backend/:
  python -m eval.expert_agreement --labels eval/data/expert/agreement.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


def normalize(status: str) -> str:
    s = status.strip().lower().replace(" ", "_")
    aliases = {
        "unable": "not_assessed",
        "unable_to_assess": "not_assessed",
        "needs_improvement": "failed",
        "complete": "passed",
        "completed": "passed",
    }
    return aliases.get(s, s)


def cohen_kappa(pairs: list[tuple[str, str]]) -> float:
    """Unweighted Cohen's kappa over discrete labels present in the set."""
    if not pairs:
        return 0.0
    labels = sorted({a for a, _ in pairs} | {b for _, b in pairs})
    n = len(pairs)
    matrix = {a: Counter() for a in labels}
    for a, b in pairs:
        matrix[a][b] += 1

    agree = sum(matrix[l][l] for l in labels)
    po = agree / n

    sys_marginal = Counter(a for a, _ in pairs)
    exp_marginal = Counter(b for _, b in pairs)
    pe = sum((sys_marginal[l] / n) * (exp_marginal[l] / n) for l in labels)
    if pe >= 1.0:
        return 1.0
    return (po - pe) / (1.0 - pe)


def evaluate(path: Path) -> dict:
    pairs: list[tuple[str, str]] = []
    by_movement: dict[str, list[tuple[str, str]]] = defaultdict(list)
    confusion: Counter[tuple[str, str]] = Counter()

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"attempt_id", "movement_id", "system_status", "expert_status"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError(f"CSV must include columns: {sorted(required)}")
        for row in reader:
            sys_s = normalize(row["system_status"])
            exp_s = normalize(row["expert_status"])
            mid = row["movement_id"].strip()
            pair = (sys_s, exp_s)
            pairs.append(pair)
            by_movement[mid].append(pair)
            confusion[pair] += 1

    n = len(pairs)
    exact = sum(1 for a, b in pairs if a == b)
    agreement = exact / n if n else 0.0

    per_movement = {}
    for mid, m_pairs in sorted(by_movement.items()):
        m_exact = sum(1 for a, b in m_pairs if a == b)
        per_movement[mid] = {
            "n": len(m_pairs),
            "agreement": round(m_exact / len(m_pairs), 4),
            "cohen_kappa": round(cohen_kappa(m_pairs), 4),
        }

    return {
        "n": n,
        "exact_matches": exact,
        "agreement": round(agreement, 4),
        "cohen_kappa": round(cohen_kappa(pairs), 4),
        "per_movement": per_movement,
        "confusion": [
            {"system": a, "expert": b, "count": c}
            for (a, b), c in sorted(confusion.items(), key=lambda x: (-x[1], x[0]))
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Expert vs system agreement")
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    report = evaluate(args.labels)
    print(json.dumps(report, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
