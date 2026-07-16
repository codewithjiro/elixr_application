# Task 1 Review Package
Base: (no git — working tree snapshot)
Head: task-1 complete

## Files
- backend\config.py
- backend\assessment\tracking_confidence.py
- backend\assessment\status_reasons.py
- backend\assessment\low_confidence.py
- backend\tests\test_phase5_status.py

## FILE: backend\config.py
```
"""Shared thresholds for Phase 3 movement assessments.

Threshold sources:
- Arm Extension initial values from Phase 0 prototype tuning.
- Remaining movements use the same normalized units (shoulder-width ratios /
  degrees / consecutive frames) documented in elixr_plan.md §11–§12.
- Values are prototype defaults — adjust after expert-rated attempts (Phase 4).
"""

CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# YOLO: COCO class 39 = bottle
BOTTLE_CLASS_ID = 39
BOTTLE_CONF = 0.35
YOLO_EVERY_N_FRAMES = 3

POSE_MIN_DETECTION = 0.5
POSE_MIN_TRACKING = 0.5
LANDMARK_VISIBILITY_MIN = 0.5

# Shared timing / framing
CALIBRATION_FRAMES_REQUIRED = 12
START_FRAMES_REQUIRED = 8
HOLD_FRAMES_REQUIRED = 15
LONG_HOLD_FRAMES_REQUIRED = 45  # balanced stance ~1.5s @ 30fps / ~4.5s @ 10fps
CENTER_X_MIN = 0.30
CENTER_X_MAX = 0.70
SHOULDER_LEVEL_MAX_NORM = 0.15
STANCE_WIDTH_MIN = 0.80
STANCE_WIDTH_MAX = 1.40
STABILITY_JITTER_MAX = 0.035
TORSO_LEAN_MAX_NORM = 0.25
BOTTLE_WRIST_MAX_NORM = 0.55

# Elbow ranges (degrees)
BENT_ELBOW_MAX_DEG = 120.0
BENT_ELBOW_MIN_DEG = 60.0
EXTENDED_ELBOW_MIN_DEG = 150.0

# Bottle hold / lift relative heights (normalized image y; smaller = higher)
WAIST_Y_MIN = 0.45
WAIST_Y_MAX = 0.75
CHEST_Y_MAX = 0.55  # wrist above this (smaller y) counts as lifted to chest
SIDE_LIFT_Y_MAX = 0.50
LOWERING_START_Y_MAX = 0.50  # start must be relatively high
PATH_MIN_DELTA_Y = 0.08

# Transfer
TRANSFER_BOTTLE_WRIST_MAX = 0.60
TRANSFER_MIN_VISIBLE_RATIO = 0.5

DOMINANT_HAND = "right"
ASSESSMENT_VERSION = "3.0"

# Phase 5 tracking confidence / low-confidence latch
MIN_TRACKING_CONFIDENCE = 0.45
LOW_CONFIDENCE_FRAMES_REQUIRED = 5
LOW_CONFIDENCE_RECOVERY_FRAMES = 5

# Set ELIXR_USE_MOCK=1 to keep Phase 2 mock stream instead of live CV.
USE_MOCK_DEFAULT = False

# Movements with written rules + unit tests (Phase 3 exit).
ENABLED_MOVEMENTS = frozenset(
    {
        "ready_stance",
        "balanced_stance_hold",
        "bent_arm_preparation",
        "arm_extension",
        "toss_preparation",
        "basic_bottle_hold",
        "front_bottle_lift",
        "side_bottle_lift",
        "controlled_bottle_lowering",
        "hand_to_hand_transfer",
        "camera_test",
        "camera_readiness",
    }
)

```

## FILE: backend\assessment\tracking_confidence.py
```
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

```

## FILE: backend\assessment\status_reasons.py
```
"""Fixed status_reason enum values, priority selection, and unable-to-assess check merge."""

from __future__ import annotations

from assessment.movement_state import CheckResult

CAMERA_UNAVAILABLE = "camera_unavailable"
CAMERA_READ_FAILED = "camera_read_failed"
MODELS_UNAVAILABLE = "models_unavailable"
INTERNAL_ERROR = "internal_error"
LOW_TRACKING_CONFIDENCE = "low_tracking_confidence"
BODY_NOT_VISIBLE = "body_not_visible"
BOTTLE_NOT_VISIBLE = "bottle_not_visible"

REASON_PRIORITY: list[str] = [
    CAMERA_UNAVAILABLE,
    CAMERA_READ_FAILED,
    MODELS_UNAVAILABLE,
    INTERNAL_ERROR,
    LOW_TRACKING_CONFIDENCE,
    BODY_NOT_VISIBLE,
    BOTTLE_NOT_VISIBLE,
]

UNABLE_ASSESS_MESSAGE = "Unable to assess — tracking interrupted."


def pick_status_reason(candidates: list[str | None]) -> str | None:
    present = {c for c in candidates if c is not None}
    for reason in REASON_PRIORITY:
        if reason in present:
            return reason
    return None


def merge_checks_while_unable(
    previous: list[CheckResult],
    template: list[CheckResult],
) -> list[CheckResult]:
    passed_keys = {c.key for c in previous if c.status == "passed"}
    previous_by_key = {c.key: c for c in previous}
    template_by_key = {c.key: c for c in template}
    all_keys = list(dict.fromkeys([c.key for c in previous] + [c.key for c in template]))

    merged: list[CheckResult] = []
    for key in all_keys:
        if key in passed_keys:
            merged.append(previous_by_key[key])
            continue

        src = template_by_key.get(key) or previous_by_key[key]
        if src.status == "passed":
            merged.append(
                CheckResult(
                    key=src.key,
                    label=src.label,
                    status="not_assessed",
                    message=UNABLE_ASSESS_MESSAGE,
                    measured_value=src.measured_value,
                    expected_range=src.expected_range,
                )
            )
        else:
            merged.append(src)

    return merged

```

## FILE: backend\assessment\low_confidence.py
```
"""Debounced low-confidence latch for unable-to-assess overlay."""


class LowConfidenceGate:
    def __init__(
        self,
        *,
        min_confidence: float,
        enter_frames: int,
        recovery_frames: int,
    ) -> None:
        self._min_confidence = min_confidence
        self._enter_frames = enter_frames
        self._recovery_frames = recovery_frames
        self._latched = False
        self._low_count = 0
        self._high_count = 0

    def update(self, confidence: float) -> bool:
        if confidence < self._min_confidence:
            self._low_count += 1
            self._high_count = 0
            if not self._latched and self._low_count >= self._enter_frames:
                self._latched = True
        else:
            self._high_count += 1
            self._low_count = 0
            if self._latched and self._high_count >= self._recovery_frames:
                self._latched = False

        return self._latched

```

## FILE: backend\tests\test_phase5_status.py
```
from assessment.tracking_confidence import compute_tracking_confidence
from assessment.status_reasons import (
    CAMERA_UNAVAILABLE,
    INTERNAL_ERROR,
    LOW_TRACKING_CONFIDENCE,
    BODY_NOT_VISIBLE,
    pick_status_reason,
    merge_checks_while_unable,
)
from assessment.low_confidence import LowConfidenceGate
from assessment.movement_state import CheckResult
from config import (
    MIN_TRACKING_CONFIDENCE,
    LOW_CONFIDENCE_FRAMES_REQUIRED,
    LOW_CONFIDENCE_RECOVERY_FRAMES,
)


def test_confidence_formula():
    assert compute_tracking_confidence(body=False, bottle=False, calibrated=False) == 0.0
    assert compute_tracking_confidence(body=True, bottle=False, calibrated=False) == 0.5
    assert compute_tracking_confidence(body=True, bottle=True, calibrated=False) == 0.9
    assert compute_tracking_confidence(body=True, bottle=True, calibrated=True) == 1.0


def test_reason_priority_camera_beats_low_confidence():
    assert (
        pick_status_reason([LOW_TRACKING_CONFIDENCE, CAMERA_UNAVAILABLE, BODY_NOT_VISIBLE])
        == CAMERA_UNAVAILABLE
    )


def test_reason_priority_internal_error_above_low_confidence():
    assert (
        pick_status_reason([LOW_TRACKING_CONFIDENCE, INTERNAL_ERROR])
        == INTERNAL_ERROR
    )


def test_low_confidence_debounce_enter_and_recover():
    gate = LowConfidenceGate(
        min_confidence=MIN_TRACKING_CONFIDENCE,
        enter_frames=LOW_CONFIDENCE_FRAMES_REQUIRED,
        recovery_frames=LOW_CONFIDENCE_RECOVERY_FRAMES,
    )
    low = MIN_TRACKING_CONFIDENCE - 0.1
    high = MIN_TRACKING_CONFIDENCE + 0.1
    for _ in range(LOW_CONFIDENCE_FRAMES_REQUIRED - 1):
        assert gate.update(low) is False
    assert gate.update(low) is True
    for _ in range(LOW_CONFIDENCE_RECOVERY_FRAMES - 1):
        assert gate.update(high) is True
    assert gate.update(high) is False


def test_merge_preserves_passed_blocks_new_passes():
    previous = [
        CheckResult("a", "A", "passed", "ok"),
        CheckResult("b", "B", "in_progress", "working"),
    ]
    template = [
        CheckResult("a", "A", "passed", "ok"),
        CheckResult("b", "B", "passed", "should not promote"),
        CheckResult("c", "C", "passed", "new pass blocked"),
    ]
    merged = merge_checks_while_unable(previous, template)
    by_key = {c.key: c for c in merged}
    assert by_key["a"].status == "passed"
    assert by_key["b"].status != "passed"
    assert by_key["c"].status != "passed"

```


