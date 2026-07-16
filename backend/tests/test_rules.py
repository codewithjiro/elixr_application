"""Checkpoint / rule unit tests across the 10 movements."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from assessment.checks import (
    bottle_wrist_distance_norm,
    check_stance_width,
    finalize_status,
)
from assessment.movement_state import CheckResult, State
from assessment.rule_engine import create_assessor, is_enabled, requires_bottle
from assessment.rules.basic_bottle_hold import BasicBottleHoldAssessor
from assessment.rules.hand_to_hand_transfer import HandToHandTransferAssessor
from config import ENABLED_MOVEMENTS, START_FRAMES_REQUIRED
from tests.helpers import (
    bent_right_arm,
    bottle_near_wrist,
    default_calibration,
    standing_pose,
)


MOVEMENT_IDS = [
    "ready_stance",
    "balanced_stance_hold",
    "basic_bottle_hold",
    "front_bottle_lift",
    "side_bottle_lift",
    "bent_arm_preparation",
    "arm_extension",
    "controlled_bottle_lowering",
    "hand_to_hand_transfer",
    "toss_preparation",
]


class TestRules(unittest.TestCase):
    def test_all_ten_registered_and_enabled(self) -> None:
        cal = default_calibration()
        for mid in MOVEMENT_IDS:
            self.assertIn(mid, ENABLED_MOVEMENTS)
            self.assertTrue(is_enabled(mid))
            assessor = create_assessor(mid, cal)
            self.assertTrue(hasattr(assessor, "update"))

    def test_finalize_status_priority(self) -> None:
        self.assertEqual(
            finalize_status([CheckResult("a", "A", "not_assessed", "x")]),
            State.UNABLE_TO_ASSESS,
        )
        self.assertEqual(
            finalize_status(
                [
                    CheckResult("a", "A", "passed", "x"),
                    CheckResult("b", "B", "needs_improvement", "y"),
                ]
            ),
            State.NEEDS_IMPROVEMENT,
        )
        self.assertEqual(
            finalize_status([CheckResult("a", "A", "passed", "x")]),
            State.COMPLETED,
        )

    def test_stance_width_check(self) -> None:
        pose = standing_pose(stance=0.22)
        cal = default_calibration()
        result = check_stance_width(pose, cal.shoulder_width)
        self.assertIn(result.status, ("passed", "needs_improvement", "not_assessed"))

    def test_bottle_wrist_proximity(self) -> None:
        pose = bent_right_arm(standing_pose())
        bottle = bottle_near_wrist(pose["right_wrist"])
        d = bottle_wrist_distance_norm(
            bottle, pose["right_wrist"], 0.20, 640, 480
        )
        self.assertIsNotNone(d)
        assert d is not None
        self.assertLess(d, 0.55)

    def test_basic_bottle_hold_unable_without_pose(self) -> None:
        a = BasicBottleHoldAssessor(calibration=default_calibration())
        self.assertEqual(a.update(None, None, 640, 480), State.UNABLE_TO_ASSESS)

    def test_basic_bottle_hold_enters_start(self) -> None:
        a = BasicBottleHoldAssessor(calibration=default_calibration())
        pose = bent_right_arm(standing_pose())
        bottle = bottle_near_wrist(pose["right_wrist"])
        for _ in range(START_FRAMES_REQUIRED + 2):
            a.update(pose, bottle, 640, 480)
        self.assertIn(a.state, (State.START_POSITION, State.HOLD_CONFIRMATION))

    def test_transfer_unable_with_one_wrist_missing(self) -> None:
        a = HandToHandTransferAssessor(calibration=default_calibration())
        pose = standing_pose()
        del pose["left_wrist"]
        st = a.update(pose, None, 640, 480)
        self.assertEqual(st, State.UNABLE_TO_ASSESS)

    def test_bottle_requirement_flags(self) -> None:
        self.assertFalse(requires_bottle("ready_stance"))
        self.assertTrue(requires_bottle("arm_extension"))
        self.assertTrue(requires_bottle("hand_to_hand_transfer"))


if __name__ == "__main__":
    unittest.main()
