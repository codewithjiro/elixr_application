import tempfile
import unittest
from pathlib import Path

from eval.expert_agreement import evaluate


class ExpertAgreementTests(unittest.TestCase):
    def test_perfect_agreement(self) -> None:
        csv_text = (
            "attempt_id,movement_id,system_status,expert_status\n"
            "1,arm_extension,passed,passed\n"
            "2,arm_extension,failed,failed\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "labels.csv"
            path.write_text(csv_text, encoding="utf-8")
            report = evaluate(path)
        self.assertEqual(report["n"], 2)
        self.assertEqual(report["agreement"], 1.0)
        self.assertEqual(report["cohen_kappa"], 1.0)

    def test_per_movement_split(self) -> None:
        csv_text = (
            "attempt_id,movement_id,system_status,expert_status\n"
            "1,arm_extension,passed,failed\n"
            "2,ready_stance,passed,passed\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "labels.csv"
            path.write_text(csv_text, encoding="utf-8")
            report = evaluate(path)
        self.assertEqual(report["exact_matches"], 1)
        self.assertEqual(report["per_movement"]["ready_stance"]["agreement"], 1.0)
        self.assertEqual(report["per_movement"]["arm_extension"]["agreement"], 0.0)


if __name__ == "__main__":
    unittest.main()
