"""Unit tests for normalized geometry helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.helpers import lm, standing_pose
from vision import geometry


class TestGeometry(unittest.TestCase):
    def test_dist(self) -> None:
        self.assertAlmostEqual(geometry.dist(lm(0, 0), lm(3, 4)), 5.0, places=5)

    def test_angle_right_angle(self) -> None:
        a, b, c = lm(0, 0), lm(1, 0), lm(1, 1)
        self.assertAlmostEqual(geometry.angle_deg(a, b, c), 90.0, places=3)

    def test_angle_straight(self) -> None:
        a, b, c = lm(0, 0), lm(1, 0), lm(2, 0)
        self.assertAlmostEqual(geometry.angle_deg(a, b, c), 180.0, places=3)

    def test_shoulder_width_and_torso(self) -> None:
        pose = standing_pose()
        sw = geometry.shoulder_width(pose)
        self.assertIsNotNone(sw)
        assert sw is not None
        self.assertGreater(sw, 0)
        tc = geometry.torso_center(pose)
        self.assertIsNotNone(tc)
        assert tc is not None
        self.assertGreater(tc[0], 0.4)
        self.assertLess(tc[0], 0.6)

    def test_torso_lean_upright(self) -> None:
        pose = standing_pose()
        sw = geometry.shoulder_width(pose)
        self.assertIsNotNone(sw)
        assert sw is not None
        lean = geometry.torso_lean_norm(pose, sw)
        self.assertIsNotNone(lean)
        assert lean is not None
        self.assertLess(lean, 0.2)


if __name__ == "__main__":
    unittest.main()
