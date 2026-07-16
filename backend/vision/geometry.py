"""Normalized geometry helpers."""

from __future__ import annotations

import math

from vision.pose_detector import Landmark


def dist(a: Landmark, b: Landmark) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def angle_deg(a: Landmark, b: Landmark, c: Landmark) -> float:
    """Angle at landmark b formed by a-b-c, in degrees."""
    bax, bay = a.x - b.x, a.y - b.y
    bcx, bcy = c.x - b.x, c.y - b.y
    denom = math.hypot(bax, bay) * math.hypot(bcx, bcy)
    if denom < 1e-9:
        return 0.0
    cos_v = max(-1.0, min(1.0, (bax * bcx + bay * bcy) / denom))
    return math.degrees(math.acos(cos_v))


def shoulder_width(landmarks: dict[str, Landmark]) -> float | None:
    ls = landmarks.get("left_shoulder")
    rs = landmarks.get("right_shoulder")
    if not ls or not rs or not ls.visible or not rs.visible:
        return None
    w = dist(ls, rs)
    return w if w > 1e-6 else None


def torso_center(landmarks: dict[str, Landmark]) -> tuple[float, float] | None:
    keys = ("left_shoulder", "right_shoulder", "left_hip", "right_hip")
    pts = [landmarks[k] for k in keys if k in landmarks and landmarks[k].visible]
    if len(pts) < 4:
        return None
    return (sum(p.x for p in pts) / 4.0, sum(p.y for p in pts) / 4.0)


def torso_lean_norm(landmarks: dict[str, Landmark], shoulder_w: float) -> float | None:
    ls = landmarks.get("left_shoulder")
    rs = landmarks.get("right_shoulder")
    lh = landmarks.get("left_hip")
    rh = landmarks.get("right_hip")
    if not all(p and p.visible for p in (ls, rs, lh, rh)):
        return None
    mid_s_x = (ls.x + rs.x) / 2.0
    mid_h_x = (lh.x + rh.x) / 2.0
    return abs(mid_s_x - mid_h_x) / shoulder_w
