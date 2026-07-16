"""Synthetic landmarks / bottle boxes for rule tests."""

from __future__ import annotations

from assessment.calibration import Calibration
from vision.bottle_detector import BottleBox
from vision.pose_detector import Landmark


def lm(x: float, y: float, vis: float = 1.0) -> Landmark:
    return Landmark(x, y, 0.0, vis)


def standing_pose(
    *,
    center_x: float = 0.5,
    stance: float = 0.22,
    elbow_bend_right: float = 90.0,
) -> dict[str, Landmark]:
    """Rough standing skeleton in normalized coords."""
    sw = 0.20  # shoulder width in x
    # elbow angle approximated by placing elbow relative to shoulder/wrist
    # For 90° bent right arm: wrist near hip-ish, elbow out
    return {
        "left_shoulder": lm(center_x - sw / 2, 0.32),
        "right_shoulder": lm(center_x + sw / 2, 0.32),
        "left_elbow": lm(center_x - sw / 2 - 0.05, 0.45),
        "right_elbow": lm(center_x + sw / 2 + 0.08, 0.42),
        "left_wrist": lm(center_x - sw / 2 - 0.02, 0.58),
        "right_wrist": lm(center_x + sw / 2 + 0.02, 0.58),
        "left_hip": lm(center_x - 0.08, 0.55),
        "right_hip": lm(center_x + 0.08, 0.55),
        "left_ankle": lm(center_x - stance / 2, 0.92),
        "right_ankle": lm(center_x + stance / 2, 0.92),
    }


def bent_right_arm(pose: dict[str, Landmark]) -> dict[str, Landmark]:
    """Force right arm into a clearly bent configuration (~90°)."""
    out = dict(pose)
    out["right_shoulder"] = lm(0.60, 0.32)
    out["right_elbow"] = lm(0.72, 0.45)
    out["right_wrist"] = lm(0.60, 0.58)
    return out


def extended_right_arm(pose: dict[str, Landmark]) -> dict[str, Landmark]:
    out = dict(pose)
    out["right_shoulder"] = lm(0.60, 0.32)
    out["right_elbow"] = lm(0.70, 0.32)
    out["right_wrist"] = lm(0.82, 0.32)
    return out


def bottle_near_wrist(
    wrist: Landmark,
    frame_w: int = 640,
    frame_h: int = 480,
    conf: float = 0.9,
) -> BottleBox:
    cx = wrist.x * frame_w
    cy = wrist.y * frame_h
    return BottleBox(cx - 20, cy - 40, cx + 20, cy + 40, conf)


def default_calibration(hand: str = "right") -> Calibration:
    return Calibration(
        shoulder_width=0.20,
        torso_center=(0.5, 0.45),
        approx_arm_length=0.28,
        dominant_hand=hand,
        ready=True,
    )
