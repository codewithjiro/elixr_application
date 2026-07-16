"""Reusable normalized checkpoint helpers (not grip/rotation claims)."""

from __future__ import annotations

from vision import geometry
from vision.bottle_detector import BottleBox
from vision.pose_detector import Landmark

from assessment.movement_state import CheckResult, State
from config import (
    BOTTLE_WRIST_MAX_NORM,
    CENTER_X_MAX,
    CENTER_X_MIN,
    SHOULDER_LEVEL_MAX_NORM,
    STANCE_WIDTH_MAX,
    STANCE_WIDTH_MIN,
    TORSO_LEAN_MAX_NORM,
)


REQUIRED_FULL_BODY = (
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
    "left_ankle",
    "right_ankle",
)


def required_visible(
    landmarks: dict[str, Landmark] | None,
    keys: tuple[str, ...],
) -> bool:
    if landmarks is None:
        return False
    for k in keys:
        lm = landmarks.get(k)
        if lm is None or not lm.visible:
            return False
    return True


def arm_landmarks(
    landmarks: dict[str, Landmark],
    side: str,
) -> tuple[Landmark, Landmark, Landmark] | None:
    s = landmarks.get(f"{side}_shoulder")
    e = landmarks.get(f"{side}_elbow")
    w = landmarks.get(f"{side}_wrist")
    if not all(p and p.visible for p in (s, e, w)):
        return None
    return s, e, w  # type: ignore[return-value]


def bottle_center_norm(
    bottle: BottleBox,
    frame_w: int,
    frame_h: int,
) -> tuple[float, float]:
    cx = ((bottle.xmin + bottle.xmax) / 2.0) / frame_w
    cy = ((bottle.ymin + bottle.ymax) / 2.0) / frame_h
    return cx, cy


def bottle_wrist_distance_norm(
    bottle: BottleBox | None,
    wrist: Landmark,
    shoulder_width: float,
    frame_w: int,
    frame_h: int,
) -> float | None:
    if bottle is None or shoulder_width < 1e-6:
        return None
    cx, cy = bottle_center_norm(bottle, frame_w, frame_h)
    return geometry.dist(
        Landmark(cx, cy, 0.0, 1.0),
        Landmark(wrist.x, wrist.y, 0.0, 1.0),
    ) / shoulder_width


def stance_width_norm(
    landmarks: dict[str, Landmark],
    shoulder_width: float,
) -> float | None:
    la = landmarks.get("left_ankle")
    ra = landmarks.get("right_ankle")
    if not la or not ra or not la.visible or not ra.visible:
        return None
    if shoulder_width < 1e-6:
        return None
    return geometry.dist(la, ra) / shoulder_width


def shoulder_level_norm(
    landmarks: dict[str, Landmark],
    shoulder_width: float,
) -> float | None:
    ls = landmarks.get("left_shoulder")
    rs = landmarks.get("right_shoulder")
    if not ls or not rs or not ls.visible or not rs.visible:
        return None
    if shoulder_width < 1e-6:
        return None
    return abs(ls.y - rs.y) / shoulder_width


def torso_centered(landmarks: dict[str, Landmark]) -> tuple[bool, float | None]:
    tc = geometry.torso_center(landmarks)
    if tc is None:
        return False, None
    ok = CENTER_X_MIN <= tc[0] <= CENTER_X_MAX
    return ok, tc[0]


def check_body_visibility(
    landmarks: dict[str, Landmark] | None,
    keys: tuple[str, ...] = REQUIRED_FULL_BODY,
) -> CheckResult:
    ok = required_visible(landmarks, keys)
    return CheckResult(
        "body_visibility",
        "Body visibility",
        "passed" if ok else "not_assessed",
        "Required landmarks visible." if ok else "Required body landmarks not visible.",
    )


def check_bottle_visibility(bottle: BottleBox | None) -> CheckResult:
    ok = bottle is not None
    return CheckResult(
        "bottle_visibility",
        "Bottle visibility",
        "passed" if ok else "not_assessed",
        "Bottle detected." if ok else "Bottle not detected; cannot assess.",
        measured_value=None if bottle is None else round(bottle.confidence, 3),
        expected_range="bottle class above confidence",
    )


def check_stance_width(
    landmarks: dict[str, Landmark],
    shoulder_width: float,
) -> CheckResult:
    val = stance_width_norm(landmarks, shoulder_width)
    if val is None:
        return CheckResult(
            "stance_width",
            "Stance width",
            "not_assessed",
            "Ankles not visible.",
            expected_range=f"{STANCE_WIDTH_MIN}-{STANCE_WIDTH_MAX} shoulder widths",
        )
    ok = STANCE_WIDTH_MIN <= val <= STANCE_WIDTH_MAX
    return CheckResult(
        "stance_width",
        "Stance width",
        "passed" if ok else "needs_improvement",
        "Stance width within range." if ok else "Adjust feet closer to shoulder width.",
        measured_value=round(val, 3),
        expected_range=f"{STANCE_WIDTH_MIN}-{STANCE_WIDTH_MAX} shoulder widths",
    )


def check_shoulder_level(
    landmarks: dict[str, Landmark],
    shoulder_width: float,
) -> CheckResult:
    val = shoulder_level_norm(landmarks, shoulder_width)
    if val is None:
        return CheckResult(
            "shoulder_level",
            "Shoulder level",
            "not_assessed",
            "Shoulders not visible.",
            expected_range=f"<= {SHOULDER_LEVEL_MAX_NORM}",
        )
    ok = val <= SHOULDER_LEVEL_MAX_NORM
    return CheckResult(
        "shoulder_level",
        "Shoulder level",
        "passed" if ok else "needs_improvement",
        "Shoulders level." if ok else "Keep shoulders level.",
        measured_value=round(val, 3),
        expected_range=f"<= {SHOULDER_LEVEL_MAX_NORM}",
    )


def check_torso_center(landmarks: dict[str, Landmark]) -> CheckResult:
    ok, x = torso_centered(landmarks)
    if x is None:
        return CheckResult(
            "body_centering",
            "Body centering",
            "not_assessed",
            "Could not locate torso center.",
            expected_range=f"x in [{CENTER_X_MIN}, {CENTER_X_MAX}]",
        )
    return CheckResult(
        "body_centering",
        "Body centering",
        "passed" if ok else "needs_improvement",
        "Centered in frame." if ok else "Move to the center of the camera view.",
        measured_value=round(x, 3),
        expected_range=f"x in [{CENTER_X_MIN}, {CENTER_X_MAX}]",
    )


def check_bottle_wrist(
    bottle: BottleBox | None,
    wrist: Landmark | None,
    shoulder_width: float,
    frame_w: int,
    frame_h: int,
    max_norm: float = BOTTLE_WRIST_MAX_NORM,
) -> CheckResult:
    if wrist is None:
        return CheckResult(
            "bottle_wrist",
            "Bottle near wrist",
            "not_assessed",
            "Wrist not visible.",
            expected_range=f"<= {max_norm}",
        )
    dist_n = bottle_wrist_distance_norm(
        bottle, wrist, shoulder_width, frame_w, frame_h
    )
    if dist_n is None:
        return CheckResult(
            "bottle_wrist",
            "Bottle near wrist",
            "not_assessed",
            "Bottle not detected; cannot verify proximity.",
            expected_range=f"<= {max_norm}",
        )
    ok = dist_n <= max_norm
    return CheckResult(
        "bottle_wrist",
        "Bottle near wrist",
        "passed" if ok else "needs_improvement",
        "Bottle near wrist." if ok else "Keep the bottle near your wrist.",
        measured_value=round(dist_n, 3),
        expected_range=f"<= {max_norm}",
    )


def check_torso_lean(
    landmarks: dict[str, Landmark],
    shoulder_width: float,
) -> CheckResult:
    lean = geometry.torso_lean_norm(landmarks, shoulder_width)
    if lean is None:
        return CheckResult(
            "torso_lean",
            "Limited torso lean",
            "not_assessed",
            "Could not measure torso lean.",
            expected_range=f"<= {TORSO_LEAN_MAX_NORM}",
        )
    ok = lean <= TORSO_LEAN_MAX_NORM
    return CheckResult(
        "torso_lean",
        "Limited torso lean",
        "passed" if ok else "needs_improvement",
        "Torso upright." if ok else "Keep your torso upright.",
        measured_value=round(lean, 3),
        expected_range=f"<= {TORSO_LEAN_MAX_NORM}",
    )


def finalize_status(checks: list[CheckResult]) -> State:
    """Map checkpoint list to terminal assessment state."""
    if any(c.status == "not_assessed" for c in checks):
        return State.UNABLE_TO_ASSESS
    if any(c.status == "needs_improvement" for c in checks):
        return State.NEEDS_IMPROVEMENT
    return State.COMPLETED
