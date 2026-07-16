"""Per-session calibration from standing pose."""

from __future__ import annotations

from dataclasses import dataclass

from vision import geometry
from vision.pose_detector import Landmark


@dataclass
class Calibration:
    shoulder_width: float
    torso_center: tuple[float, float]
    approx_arm_length: float
    dominant_hand: str
    ready: bool = True


def calibrate(
    landmarks: dict[str, Landmark],
    dominant_hand: str,
) -> Calibration | None:
    sw = geometry.shoulder_width(landmarks)
    tc = geometry.torso_center(landmarks)
    if sw is None or tc is None:
        return None

    side = "right" if dominant_hand == "right" else "left"
    shoulder = landmarks.get(f"{side}_shoulder")
    wrist = landmarks.get(f"{side}_wrist")
    if not shoulder or not wrist or not shoulder.visible or not wrist.visible:
        return None

    arm_len = geometry.dist(shoulder, wrist)
    if arm_len < 1e-6:
        return None

    return Calibration(
        shoulder_width=sw,
        torso_center=tc,
        approx_arm_length=arm_len,
        dominant_hand=dominant_hand,
        ready=True,
    )
