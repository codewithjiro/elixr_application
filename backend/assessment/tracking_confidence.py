"""Composite tracking confidence from body, bottle, and calibration signals."""


def compute_tracking_confidence(*, body: bool, bottle: bool, calibrated: bool) -> float:
    conf = 0.0
    if body:
        conf += 0.5
    if bottle:
        conf += 0.4
    if calibrated:
        conf += 0.1
    return min(1.0, conf)
