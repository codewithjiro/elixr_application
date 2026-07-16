"""State machine transition tests for selected movements."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from assessment.movement_state import State
from assessment.rules.arm_extension import ArmExtensionAssessor
from assessment.rules.ready_stance import ReadyStanceAssessor
from config import HOLD_FRAMES_REQUIRED, START_FRAMES_REQUIRED
from tests.helpers import (
    bent_right_arm,
    bottle_near_wrist,
    default_calibration,
    extended_right_arm,
    standing_pose,
)


def _drive(assessor, pose_fn, frames: int, bottle_fn=None) -> None:
    for _ in range(frames):
        pose = pose_fn()
        bottle = bottle_fn(pose) if bottle_fn else None
        assessor.update(pose, bottle, 640, 480)


class TestStateMachines(unittest.TestCase):
    def test_ready_stance_reaches_hold_then_complete(self) -> None:
        a = ReadyStanceAssessor(calibration=default_calibration())
        _drive(a, standing_pose, START_FRAMES_REQUIRED)
        self.assertIn(
            a.state, (State.START_POSITION, State.HOLD_CONFIRMATION)
        )
        _drive(a, standing_pose, HOLD_FRAMES_REQUIRED + 5)
        self.assertIn(
            a.state,
            (State.COMPLETED, State.NEEDS_IMPROVEMENT, State.HOLD_CONFIRMATION),
        )

    def test_arm_extension_unable_without_landmarks(self) -> None:
        a = ArmExtensionAssessor(calibration=default_calibration())
        st = a.update(None, None, 640, 480)
        self.assertEqual(st, State.UNABLE_TO_ASSESS)

    def test_arm_extension_progresses_from_bent_to_extended(self) -> None:
        a = ArmExtensionAssessor(calibration=default_calibration())

        def bent():
            return bent_right_arm(standing_pose())

        def bottle(pose):
            return bottle_near_wrist(pose["right_wrist"])

        _drive(a, bent, START_FRAMES_REQUIRED + 2, bottle)
        self.assertIn(
            a.state,
            (State.START_POSITION, State.MOVEMENT_IN_PROGRESS, State.NOT_READY),
        )

        mid = bent()
        mid["right_elbow"] = mid["right_elbow"].__class__(0.70, 0.38, 0.0, 1.0)
        mid["right_wrist"] = mid["right_wrist"].__class__(0.78, 0.35, 0.0, 1.0)
        for _ in range(3):
            a.update(mid, bottle(mid), 640, 480)

        def extended():
            return extended_right_arm(standing_pose())

        for _ in range(HOLD_FRAMES_REQUIRED + 20):
            pose = extended()
            a.update(pose, bottle(pose), 640, 480)

        self.assertIn(
            a.state,
            (
                State.COMPLETED,
                State.NEEDS_IMPROVEMENT,
                State.HOLD_CONFIRMATION,
                State.END_POSITION,
                State.MOVEMENT_IN_PROGRESS,
            ),
        )


if __name__ == "__main__":
    unittest.main()
