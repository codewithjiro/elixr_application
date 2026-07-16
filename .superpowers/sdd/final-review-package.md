# Phase 5 Final Review Package (no git — key file snapshot)
Progress ledger:
# Phase 5 SDD Progress

Workspace: no git repository — skip commits; review via file snapshots.

Task 1: complete (no git commits; review clean)

Task 2: complete (no git; review approved after camera/model recovery + cumulative passes; duplicate test removed)

Task 3: complete (no git; review clean after banner priority fix)

Task 4: complete (no git; §20 onboarding/camera + safety gate; manual camera smoke deferred to human)

Task 5: complete (no git; docs review approved)



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
## FILE: backend\assessment\live_session.py
```
"""Live CV assessment session for WebSocket (Phase 3)."""

from __future__ import annotations

import base64
import os
import time
from typing import Any, Optional

import cv2
import numpy as np

from assessment.calibration import Calibration, calibrate
from assessment.checks import check_body_visibility, check_bottle_visibility
from assessment.low_confidence import LowConfidenceGate
from assessment.movement_state import CheckResult, State, TERMINAL_STATES
from assessment.rule_engine import (
    create_assessor,
    is_enabled,
    requires_bottle,
    step_label,
)
from assessment.status_reasons import (
    BODY_NOT_VISIBLE,
    BOTTLE_NOT_VISIBLE,
    CAMERA_READ_FAILED,
    CAMERA_UNAVAILABLE,
    INTERNAL_ERROR,
    LOW_TRACKING_CONFIDENCE,
    MODELS_UNAVAILABLE,
    merge_checks_while_unable,
    pick_status_reason,
)
from assessment.tracking_confidence import compute_tracking_confidence
from config import (
    ASSESSMENT_VERSION,
    CALIBRATION_FRAMES_REQUIRED,
    CAMERA_INDEX,
    FRAME_HEIGHT,
    FRAME_WIDTH,
    LOW_CONFIDENCE_FRAMES_REQUIRED,
    LOW_CONFIDENCE_RECOVERY_FRAMES,
    MIN_TRACKING_CONFIDENCE,
    YOLO_EVERY_N_FRAMES,
)
from schemas.frame_event import CheckpointUpdate, FrameEvent
from schemas.session_result import SessionSummary
from vision.bottle_detector import BottleDetector
from vision.pose_detector import PoseDetector
from vision.smoothing import Smoother


STATUS_MESSAGES = {
    CAMERA_UNAVAILABLE: "Webcam unavailable or busy. Close other camera apps and check the camera index.",
    CAMERA_READ_FAILED: "Camera frame read failed. Reconnect the camera and restart the session.",
    MODELS_UNAVAILABLE: "Vision models failed to load. Check Python dependencies and model weights.",
    INTERNAL_ERROR: "Unexpected assessment error. Restart the session and check backend logs.",
    LOW_TRACKING_CONFIDENCE: "Improve lighting and framing, then hold steady.",
    BODY_NOT_VISIBLE: "Stand fully in frame, front-facing, and hold steady.",
    BOTTLE_NOT_VISIBLE: "Use an opaque plastic practice bottle and improve lighting.",
}


def _checks_to_updates(checks: list[CheckResult]) -> list[CheckpointUpdate]:
    return [
        CheckpointUpdate(
            key=c.key,
            status=c.status,
            message=c.message,
            measured_value=c.measured_value,
            expected_range=c.expected_range,
        )
        for c in checks
    ]


def should_freeze_assessor(*, latched: bool, hard_unable: bool) -> bool:
    return latched or hard_unable


def update_validated_checks(
    previous: list[CheckResult],
    current: list[CheckResult],
) -> list[CheckResult]:
    """Accumulate passed checkpoints without allowing later frames to erase them."""
    passed_by_key = {check.key: check for check in previous if check.status == "passed"}
    for check in current:
        if check.status == "passed" and check.key not in passed_by_key:
            passed_by_key[check.key] = check
    return list(passed_by_key.values())


class LiveAssessmentSession:
    """Webcam + pose + YOLO + movement state machine."""

    def __init__(
        self,
        movement_id: str,
        dominant_hand: str = "right",
        mirror_camera: bool = True,
        camera_index: int = CAMERA_INDEX,
    ) -> None:
        if not is_enabled(movement_id) and movement_id not in (
            "camera_test",
            "camera_readiness",
        ):
            raise ValueError(f"Movement '{movement_id}' is not enabled for assessment.")

        self.movement_id = movement_id
        self.dominant_hand = dominant_hand
        self.mirror_camera = mirror_camera
        self.camera_index = camera_index
        self.started_at = time.monotonic()
        self.frame_index = 0
        self.camera_source = "placeholder"
        self.detection_interruptions = 0
        self.attempt_count = 1

        self._cap: Optional[cv2.VideoCapture] = None
        self._pose: Optional[PoseDetector] = None
        self._bottle_det: Optional[BottleDetector] = None
        self._smoother = Smoother(window=5)
        self._calibration: Calibration | None = None
        self._calib_frames = 0
        self._assessor: Any = None
        self._last_checks: list[CheckResult] = []
        self._last_validated_checks: list[CheckResult] = []
        self._pipeline_state = State.CAMERA_READY
        self._models_ok = False
        self._camera_failure_reason: str | None = None
        self._low_confidence_gate = LowConfidenceGate(
            min_confidence=MIN_TRACKING_CONFIDENCE,
            enter_frames=LOW_CONFIDENCE_FRAMES_REQUIRED,
            recovery_frames=LOW_CONFIDENCE_RECOVERY_FRAMES,
        )

        self._open_camera()
        self._init_models()

    def _open_camera(self) -> None:
        try:
            cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap.release()
                cap = cv2.VideoCapture(self.camera_index)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
                self._cap = cap
                self.camera_source = "webcam"
                self._camera_failure_reason = None
            else:
                cap.release()
                self._camera_failure_reason = CAMERA_UNAVAILABLE
                self.detection_interruptions += 1
        except Exception:
            self._cap = None
            self.camera_source = "placeholder"
            self._camera_failure_reason = CAMERA_UNAVAILABLE
            self.detection_interruptions += 1

    def _release_camera(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def _ensure_camera(self) -> bool:
        if self._cap is None:
            self._open_camera()
        return self._cap is not None and self._camera_failure_reason is None

    def _init_models(self) -> None:
        try:
            self._pose = PoseDetector()
            self._bottle_det = BottleDetector("yolo11n.pt")
            self._models_ok = True
        except Exception:
            self._models_ok = False
            self.detection_interruptions += 1

    def _ensure_models(self) -> None:
        if self._models_ok and self._pose is not None and self._bottle_det is not None:
            return
        self._init_models()

    def close(self) -> None:
        self._release_camera()
        if self._pose is not None:
            try:
                self._pose.close()
            except Exception:
                pass
            self._pose = None

    @property
    def elapsed_seconds(self) -> int:
        return int(time.monotonic() - self.started_at)

    def _build_placeholder(self, message: str) -> np.ndarray:
        frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
        frame[:] = (28, 28, 36)
        cv2.putText(
            frame,
            "ELIXR Phase 3",
            (24, 48),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 120, 180),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            f"Movement: {self.movement_id}",
            (24, 96),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (240, 240, 245),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            message,
            (24, 140),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (251, 191, 36),
            1,
            cv2.LINE_AA,
        )
        return frame

    def _read_frame(self) -> np.ndarray:
        if self._cap is not None:
            ok, frame = self._cap.read()
            if ok and frame is not None:
                if self.mirror_camera:
                    frame = cv2.flip(frame, 1)
                return cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
            self._release_camera()
            self.camera_source = "placeholder"
            self._camera_failure_reason = CAMERA_READ_FAILED
            self.detection_interruptions += 1
        return self._build_placeholder("Webcam unavailable — placeholder frame")

    def _encode_jpeg(self, frame: np.ndarray) -> str:
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if not ok:
            return ""
        return base64.b64encode(buf.tobytes()).decode("ascii")

    def _is_camera_test(self) -> bool:
        return self.movement_id in ("camera_test", "camera_readiness")

    def next_frame_event(self) -> FrameEvent:
        try:
            return self._next_frame_event()
        except Exception:
            self.detection_interruptions += 1
            self._pipeline_state = State.UNABLE_TO_ASSESS
            checks = merge_checks_while_unable(
                self._last_validated_checks,
                self._last_checks,
            )
            self._last_checks = checks
            frame = self._build_placeholder(STATUS_MESSAGES[INTERNAL_ERROR])
            return FrameEvent(
                movement_id=self.movement_id,
                assessment_state=State.UNABLE_TO_ASSESS.value,
                body_detected=False,
                bottle_detected=False,
                tracking_confidence=0.0,
                current_step="unable_to_assess",
                checks=_checks_to_updates(checks),
                frame_jpeg_base64=self._encode_jpeg(frame),
                camera_source=self.camera_source,
                status_reason=pick_status_reason([INTERNAL_ERROR]),
                status_message=STATUS_MESSAGES[INTERNAL_ERROR],
            )

    def _next_frame_event(self) -> FrameEvent:
        self.frame_index += 1
        self._ensure_camera()
        self._ensure_models()
        frame = self._read_frame()
        h, w = frame.shape[:2]

        hard_reason = pick_status_reason(
            [
                self._camera_failure_reason,
                (
                    MODELS_UNAVAILABLE
                    if not self._models_ok
                    or self._pose is None
                    or self._bottle_det is None
                    else None
                ),
            ]
        )
        if should_freeze_assessor(latched=False, hard_unable=hard_reason is not None):
            assert hard_reason is not None
            jpeg = self._encode_jpeg(
                self._build_placeholder(STATUS_MESSAGES[hard_reason])
            )
            template = [
                CheckResult(
                    hard_reason,
                    "Assessment unavailable",
                    "not_assessed",
                    STATUS_MESSAGES[hard_reason],
                )
            ]
            checks = merge_checks_while_unable(
                self._last_validated_checks,
                template,
            )
            self._last_checks = checks
            self._pipeline_state = State.UNABLE_TO_ASSESS
            return FrameEvent(
                movement_id=self.movement_id,
                assessment_state=State.UNABLE_TO_ASSESS.value,
                body_detected=False,
                bottle_detected=False,
                tracking_confidence=0.0,
                current_step="unable_to_assess",
                checks=_checks_to_updates(checks),
                frame_jpeg_base64=jpeg,
                camera_source=self.camera_source,
                status_reason=hard_reason,
                status_message=STATUS_MESSAGES[hard_reason],
            )

        landmarks = self._pose.process(frame)
        landmarks = self._smoother.push_landmarks(landmarks)

        bottle = None
        if self.frame_index % YOLO_EVERY_N_FRAMES == 0:
            bottle = self._bottle_det.detect(frame)
        else:
            bottle = self._bottle_det.last
        bottle = self._smoother.push_bottle(bottle)

        self._pose.draw(frame, landmarks)
        if bottle is not None:
            cv2.rectangle(
                frame,
                (int(bottle.xmin), int(bottle.ymin)),
                (int(bottle.xmax), int(bottle.ymax)),
                (255, 77, 141),
                2,
            )

        body = landmarks is not None
        bottle_ok = bottle is not None
        conf = compute_tracking_confidence(
            body=body,
            bottle=bottle_ok,
            calibrated=self._calibration is not None,
        )
        latched = self._low_confidence_gate.update(conf)
        status_reason = pick_status_reason(
            [
                LOW_TRACKING_CONFIDENCE if latched else None,
                BODY_NOT_VISIBLE if not body else None,
                (
                    BOTTLE_NOT_VISIBLE
                    if requires_bottle(self.movement_id) and not bottle_ok
                    else None
                ),
            ]
        )

        if should_freeze_assessor(latched=latched, hard_unable=False):
            template = [check_body_visibility(landmarks)]
            if requires_bottle(self.movement_id):
                template.append(check_bottle_visibility(bottle))
            checks = merge_checks_while_unable(
                self._last_validated_checks,
                template,
            )
            self._last_checks = checks
            self._pipeline_state = State.UNABLE_TO_ASSESS
            jpeg = self._encode_jpeg(frame)
            return FrameEvent(
                movement_id=self.movement_id,
                assessment_state=State.UNABLE_TO_ASSESS.value,
                body_detected=body,
                bottle_detected=bottle_ok,
                tracking_confidence=conf,
                current_step="unable_to_assess",
                checks=_checks_to_updates(checks),
                frame_jpeg_base64=jpeg,
                camera_source=self.camera_source,
                status_reason=status_reason,
                status_message=STATUS_MESSAGES[status_reason] if status_reason else None,
            )

        # Camera test: readiness only
        if self._is_camera_test():
            checks = [
                check_body_visibility(landmarks),
                check_bottle_visibility(bottle),
            ]
            self._last_checks = checks
            self._last_validated_checks = update_validated_checks(
                self._last_validated_checks,
                checks,
            )
            state = (
                State.CAMERA_READY
                if checks[0].status == "passed"
                else State.NOT_READY
            )
            jpeg = self._encode_jpeg(frame)
            return FrameEvent(
                movement_id=self.movement_id,
                assessment_state=state.value,
                body_detected=body,
                bottle_detected=bottle_ok,
                tracking_confidence=conf,
                current_step="readiness_check",
                checks=_checks_to_updates(checks),
                frame_jpeg_base64=jpeg,
                camera_source=self.camera_source,
                status_reason=status_reason,
                status_message=STATUS_MESSAGES[status_reason] if status_reason else None,
            )

        # Calibration phase
        if self._calibration is None:
            self._pipeline_state = State.CALIBRATING
            if landmarks is not None:
                cal = calibrate(landmarks, self.dominant_hand)
                if cal is not None:
                    self._calib_frames += 1
                else:
                    self._calib_frames = 0
                if self._calib_frames >= CALIBRATION_FRAMES_REQUIRED and cal is not None:
                    self._calibration = cal
                    self._assessor = create_assessor(self.movement_id, cal)
                    self._pipeline_state = State.NOT_READY

            checks = [
                check_body_visibility(landmarks),
                CheckResult(
                    "calibration",
                    "Calibration",
                    "in_progress",
                    f"Hold ready stance… {self._calib_frames}/{CALIBRATION_FRAMES_REQUIRED}",
                    measured_value=float(self._calib_frames),
                    expected_range=f">= {CALIBRATION_FRAMES_REQUIRED} frames",
                ),
            ]
            if requires_bottle(self.movement_id):
                checks.append(check_bottle_visibility(bottle))
            self._last_checks = checks
            self._last_validated_checks = update_validated_checks(
                self._last_validated_checks,
                checks,
            )
            jpeg = self._encode_jpeg(frame)
            return FrameEvent(
                movement_id=self.movement_id,
                assessment_state=State.CALIBRATING.value,
                body_detected=body,
                bottle_detected=bottle_ok,
                tracking_confidence=conf,
                current_step="calibration",
                checks=_checks_to_updates(checks),
                frame_jpeg_base64=jpeg,
                camera_source=self.camera_source,
                status_reason=status_reason,
                status_message=STATUS_MESSAGES[status_reason] if status_reason else None,
            )

        assert self._assessor is not None
        st = self._assessor.update(landmarks, bottle, w, h)
        self._pipeline_state = st
        live_checks: list[CheckResult] = list(getattr(self._assessor, "checks", []) or [])
        if not live_checks:
            live_checks = [
                CheckResult(
                    "progress",
                    "Assessment progress",
                    "in_progress",
                    f"State: {st.value}",
                )
            ]
            if requires_bottle(self.movement_id):
                live_checks.insert(0, check_bottle_visibility(bottle))
            live_checks.insert(0, check_body_visibility(landmarks))
        self._last_checks = live_checks
        self._last_validated_checks = update_validated_checks(
            self._last_validated_checks,
            live_checks,
        )

        cv2.putText(
            frame,
            f"{self.movement_id} · {st.value}",
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 77, 141),
            2,
            cv2.LINE_AA,
        )

        jpeg = self._encode_jpeg(frame)
        return FrameEvent(
            movement_id=self.movement_id,
            assessment_state=st.value,
            body_detected=body,
            bottle_detected=bottle_ok,
            tracking_confidence=conf,
            current_step=step_label(st),
            checks=_checks_to_updates(live_checks),
            frame_jpeg_base64=jpeg,
            camera_source=self.camera_source,
            status_reason=status_reason,
            status_message=STATUS_MESSAGES[status_reason] if status_reason else None,
        )

    def build_summary(self) -> SessionSummary:
        checks = _checks_to_updates(self._last_checks)
        # Prefer terminal assessor checks
        if self._assessor is not None and getattr(self._assessor, "checks", None):
            checks = _checks_to_updates(self._assessor.checks)
            st = self._assessor.state
        else:
            st = self._pipeline_state

        passed = sum(1 for c in checks if c.status == "passed")
        failed = sum(1 for c in checks if c.status == "needs_improvement")
        not_assessed = sum(
            1 for c in checks if c.status in ("not_assessed", "in_progress")
        )

        if st in TERMINAL_STATES:
            result = st.value
        elif self._is_camera_test():
            result = "completed" if passed > 0 and not_assessed == 0 else "not_assessed"
        elif passed > 0 and failed == 0 and not_assessed == 0:
            result = "completed"
        elif not_assessed > 0 and passed == 0:
            result = "unable_to_assess"
        elif failed > 0:
            result = "needs_improvement"
        else:
            result = "not_assessed"

        return SessionSummary(
            movement_id=self.movement_id,
            result_status=result,
            duration_seconds=max(self.elapsed_seconds, 1),
            attempt_count=self.attempt_count,
            passed_check_count=passed,
            failed_check_count=failed,
            not_assessed_count=not_assessed,
            detection_interruptions=self.detection_interruptions,
            assessment_version=ASSESSMENT_VERSION,
            checks=checks,
            message="Phase 3 live CV assessment.",
        )


def create_session(
    movement_id: str,
    dominant_hand: str = "right",
    mirror_camera: bool = True,
) -> LiveAssessmentSession | Any:
    """Factory: live CV unless ELIXR_USE_MOCK=1."""
    use_mock = os.environ.get("ELIXR_USE_MOCK", "").strip() in ("1", "true", "yes")
    if use_mock:
        from mock_stream import MockAssessmentSession

        return MockAssessmentSession(
            movement_id=movement_id,
            dominant_hand=dominant_hand,
            mirror_camera=mirror_camera,
        )
    return LiveAssessmentSession(
        movement_id=movement_id,
        dominant_hand=dominant_hand,
        mirror_camera=mirror_camera,
    )

```
## FILE: backend\schemas\frame_event.py
```
from typing import Any, Optional, Union

from pydantic import BaseModel, Field


class CheckpointUpdate(BaseModel):
    key: str
    status: str
    message: str
    measured_value: Optional[Union[float, str]] = None
    expected_range: Optional[str] = None


class FrameEvent(BaseModel):
    type: str = "frame"
    movement_id: str
    assessment_state: str
    body_detected: bool
    bottle_detected: bool
    tracking_confidence: float = Field(ge=0.0, le=1.0)
    current_step: str
    checks: list[CheckpointUpdate] = Field(default_factory=list)
    frame_jpeg_base64: str
    camera_source: str = "placeholder"
    status_reason: str | None = None
    status_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

```
## FILE: backend\tests\test_phase5_status.py
```
from assessment.tracking_confidence import compute_tracking_confidence
from assessment.status_reasons import (
    CAMERA_READ_FAILED,
    CAMERA_UNAVAILABLE,
    INTERNAL_ERROR,
    LOW_TRACKING_CONFIDENCE,
    BODY_NOT_VISIBLE,
    pick_status_reason,
    merge_checks_while_unable,
)
from assessment.low_confidence import LowConfidenceGate
from assessment.live_session import (
    LiveAssessmentSession,
    should_freeze_assessor,
    update_validated_checks,
)
from assessment.movement_state import CheckResult
from config import (
    MIN_TRACKING_CONFIDENCE,
    LOW_CONFIDENCE_FRAMES_REQUIRED,
    LOW_CONFIDENCE_RECOVERY_FRAMES,
)
from schemas.frame_event import FrameEvent


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


def test_frame_event_optional_fields_omitted():
    ev = FrameEvent(
        movement_id="arm_extension",
        assessment_state="calibrating",
        body_detected=True,
        bottle_detected=False,
        tracking_confidence=0.5,
        current_step="calibration",
        frame_jpeg_base64="",
    )
    data = ev.to_dict()
    assert data.get("status_reason") in (None,)
    assert data.get("status_message") in (None,)


def test_frame_event_optional_fields_set():
    ev = FrameEvent(
        movement_id="arm_extension",
        assessment_state="unable_to_assess",
        body_detected=False,
        bottle_detected=False,
        tracking_confidence=0.2,
        current_step="unable_to_assess",
        frame_jpeg_base64="",
        status_reason=LOW_TRACKING_CONFIDENCE,
        status_message="Improve lighting and framing, then hold steady.",
    )
    assert ev.status_reason == LOW_TRACKING_CONFIDENCE


def test_should_freeze_assessor_for_latch_or_hard_unable():
    assert should_freeze_assessor(latched=False, hard_unable=False) is False
    assert should_freeze_assessor(latched=True, hard_unable=False) is True
    assert should_freeze_assessor(latched=False, hard_unable=True) is True
    assert should_freeze_assessor(latched=True, hard_unable=True) is True


def test_update_validated_checks_preserves_cumulative_passes():
    prior_a = CheckResult("a", "A", "passed", "first pass")
    previous = [
        prior_a,
        CheckResult("b", "B", "in_progress", "not validated"),
    ]
    current = [
        CheckResult("a", "A", "in_progress", "must not erase pass"),
        CheckResult("b", "B", "passed", "second pass"),
        CheckResult("c", "C", "failed", "not validated"),
    ]

    updated = update_validated_checks(previous, current)

    assert [check.key for check in updated] == ["a", "b"]
    assert updated[0] is prior_a
    assert all(check.status == "passed" for check in updated)


def test_camera_read_failure_preserves_assessment_state():
    class FailedCapture:
        released = False

        def read(self):
            return False, None

        def release(self):
            self.released = True

    session = LiveAssessmentSession.__new__(LiveAssessmentSession)
    capture = FailedCapture()
    pose = object()
    assessor = object()
    calibration = object()
    validated = [CheckResult("a", "A", "passed", "preserved")]
    session._cap = capture
    session._pose = pose
    session._assessor = assessor
    session._calibration = calibration
    session._last_validated_checks = validated
    session.mirror_camera = True
    session.camera_source = "webcam"
    session.detection_interruptions = 0
    session.movement_id = "arm_extension"

    session._read_frame()

    assert capture.released is True
    assert session._cap is None
    assert session._camera_failure_reason == CAMERA_READ_FAILED
    assert session._pose is pose
    assert session._assessor is assessor
    assert session._calibration is calibration
    assert session._last_validated_checks is validated


def test_model_init_retry_preserves_assessor_state():
    session = LiveAssessmentSession.__new__(LiveAssessmentSession)
    assessor = object()
    calibration = object()
    validated = [CheckResult("a", "A", "passed", "preserved")]
    session._models_ok = False
    session._pose = None
    session._bottle_det = None
    session._assessor = assessor
    session._calibration = calibration
    session._last_validated_checks = validated
    session.detection_interruptions = 0

    attempts = {"n": 0}

    def fake_init():
        attempts["n"] += 1
        if attempts["n"] < 2:
            session._models_ok = False
            session.detection_interruptions += 1
        else:
            session._models_ok = True
            session._pose = object()
            session._bottle_det = object()

    session._init_models = fake_init

    session._ensure_models()
    assert session._models_ok is False
    assert session._assessor is assessor
    assert session._calibration is calibration
    assert session._last_validated_checks is validated

    session._ensure_models()
    assert session._models_ok is True
    assert session._assessor is assessor
    assert session._calibration is calibration
    assert session._last_validated_checks is validated

```
## FILE: lib\core\constants\status_reasons.dart
```
class StatusReasons {
  const StatusReasons._();

  static const cameraUnavailable = 'camera_unavailable';
  static const cameraReadFailed = 'camera_read_failed';
  static const modelsUnavailable = 'models_unavailable';
  static const internalError = 'internal_error';
  static const lowTrackingConfidence = 'low_tracking_confidence';
  static const bodyNotVisible = 'body_not_visible';
  static const bottleNotVisible = 'bottle_not_visible';

  // Client-only reasons; the backend does not emit these values.
  static const backendDisconnected = 'backend_disconnected';
  static const protocolError = 'protocol_error';
}

enum StatusBannerTone { success, warning, error }

class StatusBannerInfo {
  const StatusBannerInfo({required this.message, required this.tone});

  final String message;
  final StatusBannerTone tone;
}

StatusBannerInfo? resolveStatusBanner({
  String? assessmentState,
  String? statusReason,
  String? statusMessage,
  String? clientStatusReason,
}) {
  final message = statusMessage?.trim();

  if (clientStatusReason != null) {
    return StatusBannerInfo(
      message: message?.isNotEmpty == true
          ? message!
          : _messageForReason(clientStatusReason) ??
                'The session encountered a connection error.',
      tone: _errorReasons.contains(clientStatusReason)
          ? StatusBannerTone.error
          : StatusBannerTone.warning,
    );
  }

  if (assessmentState == 'unable_to_assess') {
    return StatusBannerInfo(
      message: message?.isNotEmpty == true
          ? message!
          : _messageForReason(statusReason) ??
                'Assessment paused. Check your camera view and try again.',
      tone: StatusBannerTone.warning,
    );
  }

  return null;
}

const _errorReasons = {
  StatusReasons.cameraUnavailable,
  StatusReasons.cameraReadFailed,
  StatusReasons.modelsUnavailable,
  StatusReasons.internalError,
  StatusReasons.backendDisconnected,
  StatusReasons.protocolError,
};

String? _messageForReason(String? reason) {
  switch (reason) {
    case StatusReasons.cameraUnavailable:
      return 'Camera unavailable. Check camera access and reconnect it.';
    case StatusReasons.cameraReadFailed:
      return 'Camera feed stopped. Reconnect the camera and restart.';
    case StatusReasons.modelsUnavailable:
      return 'Assessment models are unavailable. Restart the backend.';
    case StatusReasons.internalError:
      return 'Assessment stopped unexpectedly. Restart the session.';
    case StatusReasons.lowTrackingConfidence:
      return 'Improve lighting and framing, then keep your full body visible.';
    case StatusReasons.bodyNotVisible:
      return 'Stand front-facing with your full body visible in frame.';
    case StatusReasons.bottleNotVisible:
      return 'Keep the opaque practice bottle visible and improve lighting.';
    case StatusReasons.backendDisconnected:
      return 'The backend disconnected. Check that it is running and reconnect.';
    case StatusReasons.protocolError:
      return 'The backend sent an invalid message. Restart the session.';
    default:
      return null;
  }
}

```
## FILE: lib\services\websocket_service.dart
```
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../core/constants/app_constants.dart';
import '../core/constants/status_reasons.dart';
import '../core/constants/websocket_constants.dart';

enum WsConnectionState { disconnected, connecting, connected, error }

class AssessmentCheckpoint {
  const AssessmentCheckpoint({
    required this.key,
    required this.status,
    required this.message,
    this.measuredValue,
    this.expectedRange,
  });

  final String key;
  final String status;
  final String message;
  final String? measuredValue;
  final String? expectedRange;

  String get label => key
      .split('_')
      .map((w) => w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
      .join(' ');

  /// Map backend statuses onto UI chip statuses.
  String get uiStatus {
    switch (status) {
      case 'needs_improvement':
        return AppConstants.resultPartial;
      case 'passed':
        return AppConstants.resultPassed;
      case 'failed':
        return AppConstants.resultFailed;
      case 'in_progress':
        return AppConstants.resultInProgress;
      case 'not_assessed':
        return AppConstants.resultNotAssessed;
      default:
        return status;
    }
  }

  factory AssessmentCheckpoint.fromJson(Map<String, dynamic> json) {
    final measured = json['measured_value'];
    return AssessmentCheckpoint(
      key: json['key'] as String? ?? '',
      status: json['status'] as String? ?? AppConstants.resultNotAssessed,
      message: json['message'] as String? ?? '',
      measuredValue: measured?.toString(),
      expectedRange: json['expected_range'] as String?,
    );
  }
}

class FrameEventData {
  const FrameEventData({
    required this.movementId,
    required this.assessmentState,
    required this.bodyDetected,
    required this.bottleDetected,
    required this.trackingConfidence,
    required this.currentStep,
    required this.checks,
    this.frameBytes,
    this.cameraSource,
    this.statusReason,
    this.statusMessage,
  });

  final String movementId;
  final String assessmentState;
  final bool bodyDetected;
  final bool bottleDetected;
  final double trackingConfidence;
  final String currentStep;
  final List<AssessmentCheckpoint> checks;
  final Uint8List? frameBytes;
  final String? cameraSource;
  final String? statusReason;
  final String? statusMessage;

  factory FrameEventData.fromJson(Map<String, dynamic> json) {
    Uint8List? bytes;
    final b64 = json['frame_jpeg_base64'] as String?;
    if (b64 != null && b64.isNotEmpty) {
      try {
        bytes = base64Decode(b64);
      } catch (_) {
        bytes = null;
      }
    }

    final rawChecks = json['checks'] as List<dynamic>? ?? const [];
    return FrameEventData(
      movementId: json['movement_id'] as String? ?? '',
      assessmentState: json['assessment_state'] as String? ?? '',
      bodyDetected: json['body_detected'] as bool? ?? false,
      bottleDetected: json['bottle_detected'] as bool? ?? false,
      trackingConfidence:
          (json['tracking_confidence'] as num?)?.toDouble() ?? 0,
      currentStep: json['current_step'] as String? ?? '',
      checks: rawChecks
          .whereType<Map<String, dynamic>>()
          .map(AssessmentCheckpoint.fromJson)
          .toList(),
      frameBytes: bytes,
      cameraSource: json['camera_source'] as String?,
      statusReason: json['status_reason'] as String?,
      statusMessage: json['status_message'] as String?,
    );
  }
}

class SessionSummaryData {
  const SessionSummaryData({
    required this.movementId,
    required this.resultStatus,
    required this.durationSeconds,
    required this.attemptCount,
    required this.passedCheckCount,
    required this.failedCheckCount,
    required this.notAssessedCount,
    required this.detectionInterruptions,
    required this.checks,
    this.assessmentVersion = '3.0',
    this.message,
  });

  final String movementId;
  final String resultStatus;
  final int durationSeconds;
  final int attemptCount;
  final int passedCheckCount;
  final int failedCheckCount;
  final int notAssessedCount;
  final int detectionInterruptions;
  final List<AssessmentCheckpoint> checks;
  final String assessmentVersion;
  final String? message;

  factory SessionSummaryData.fromJson(Map<String, dynamic> json) {
    final rawChecks = json['checks'] as List<dynamic>? ?? const [];
    return SessionSummaryData(
      movementId: json['movement_id'] as String? ?? '',
      resultStatus: json['result_status'] as String? ?? 'not_assessed',
      durationSeconds: (json['duration_seconds'] as num?)?.toInt() ?? 0,
      attemptCount: (json['attempt_count'] as num?)?.toInt() ?? 0,
      passedCheckCount: (json['passed_check_count'] as num?)?.toInt() ?? 0,
      failedCheckCount: (json['failed_check_count'] as num?)?.toInt() ?? 0,
      notAssessedCount: (json['not_assessed_count'] as num?)?.toInt() ?? 0,
      detectionInterruptions:
          (json['detection_interruptions'] as num?)?.toInt() ?? 0,
      assessmentVersion: json['assessment_version'] as String? ?? '3.0',
      message: json['message'] as String?,
      checks: rawChecks
          .whereType<Map<String, dynamic>>()
          .map(AssessmentCheckpoint.fromJson)
          .toList(),
    );
  }
}

/// Connects to the local FastAPI vision backend.
class WebSocketService extends ChangeNotifier {
  WebSocketService({
    this.connectTimeout = const Duration(seconds: 5),
    this.maxRetries = 3,
  });

  final Duration connectTimeout;
  final int maxRetries;

  WebSocketChannel? _channel;
  StreamSubscription? _subscription;
  Timer? _summaryTimeout;

  WsConnectionState _state = WsConnectionState.disconnected;
  String? _errorMessage;
  String? _clientStatusReason;
  FrameEventData? _latestFrame;
  SessionSummaryData? _latestSummary;
  String? _sessionMessage;
  Completer<SessionSummaryData?>? _stopCompleter;

  WsConnectionState get connectionState => _state;
  bool get isConnected => _state == WsConnectionState.connected;
  String? get errorMessage => _errorMessage;
  String? get clientStatusReason => _clientStatusReason;
  FrameEventData? get latestFrame => _latestFrame;
  SessionSummaryData? get latestSummary => _latestSummary;
  String? get sessionMessage => _sessionMessage;
  String get endpointUrl => WebSocketConstants.defaultUrl;
  String get healthUrl => WebSocketConstants.healthUrl;

  Future<bool> checkHealth({
    Duration timeout = const Duration(seconds: 3),
  }) async {
    try {
      final client = HttpClient();
      client.connectionTimeout = timeout;
      final request = await client.getUrl(Uri.parse(healthUrl));
      final response = await request.close().timeout(timeout);
      final body = await response.transform(utf8.decoder).join();
      client.close(force: true);
      if (response.statusCode != 200) {
        _setClientStatusReason(StatusReasons.backendDisconnected);
        return false;
      }
      final json = jsonDecode(body) as Map<String, dynamic>;
      final healthy = json['status'] == 'ok';
      _setClientStatusReason(
        healthy ? null : StatusReasons.backendDisconnected,
      );
      return healthy;
    } catch (_) {
      _setClientStatusReason(StatusReasons.backendDisconnected);
      return false;
    }
  }

  Future<void> connect() async {
    if (_state == WsConnectionState.connecting ||
        _state == WsConnectionState.connected) {
      return;
    }

    _setState(WsConnectionState.connecting, clearError: true);

    Object? lastError;
    for (var attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        final channel = WebSocketChannel.connect(Uri.parse(endpointUrl));
        await channel.ready.timeout(connectTimeout);
        _channel = channel;
        _subscription = channel.stream.listen(
          _onMessage,
          onError: (Object error) {
            _errorMessage = error.toString();
            _clientStatusReason = StatusReasons.backendDisconnected;
            _setState(WsConnectionState.error);
          },
          onDone: () {
            if (_state != WsConnectionState.disconnected) {
              _clientStatusReason = StatusReasons.backendDisconnected;
              _setState(WsConnectionState.disconnected);
            }
          },
          cancelOnError: true,
        );
        _clientStatusReason = null;
        _setState(WsConnectionState.connected, clearError: true);
        return;
      } catch (e) {
        lastError = e;
        await Future<void>.delayed(Duration(milliseconds: 400 * attempt));
      }
    }

    _errorMessage =
        'Could not connect to $endpointUrl after $maxRetries attempts. '
        'Is the backend running?\n($lastError)';
    _clientStatusReason = StatusReasons.backendDisconnected;
    _setState(WsConnectionState.error);
  }

  Future<void> disconnect() async {
    _summaryTimeout?.cancel();
    _summaryTimeout = null;
    await _subscription?.cancel();
    _subscription = null;
    await _channel?.sink.close();
    _channel = null;
    _latestFrame = null;
    _sessionMessage = null;
    _clientStatusReason = null;
    if (_stopCompleter != null && !_stopCompleter!.isCompleted) {
      _stopCompleter!.complete(null);
    }
    _stopCompleter = null;
    _setState(WsConnectionState.disconnected);
  }

  void sendMessage(Map<String, dynamic> message) {
    if (_channel == null || !isConnected) {
      _errorMessage = 'Not connected to backend';
      _clientStatusReason = StatusReasons.backendDisconnected;
      notifyListeners();
      return;
    }
    _channel!.sink.add(jsonEncode(message));
  }

  void startSession({
    required String movementId,
    String dominantHand = AppConstants.dominantHandRight,
    bool mirrorCamera = true,
  }) {
    _latestSummary = null;
    _latestFrame = null;
    _sessionMessage = null;
    sendMessage({
      'action': 'start',
      'movement_id': movementId,
      'dominant_hand': dominantHand,
      'mirror_camera': mirrorCamera,
    });
    notifyListeners();
  }

  /// Sends stop and waits for `session_summary` (or timeout).
  Future<SessionSummaryData?> stopSession({
    Duration timeout = const Duration(seconds: 4),
  }) async {
    if (!isConnected) return _latestSummary;

    _stopCompleter = Completer<SessionSummaryData?>();
    sendMessage({'action': 'stop'});

    _summaryTimeout?.cancel();
    _summaryTimeout = Timer(timeout, () {
      if (_stopCompleter != null && !_stopCompleter!.isCompleted) {
        _stopCompleter!.complete(_latestSummary);
      }
    });

    final summary = await _stopCompleter!.future;
    _summaryTimeout?.cancel();
    _stopCompleter = null;
    return summary;
  }

  Future<void> cancelSession() async {
    sendMessage({'action': 'cancel'});
    _latestFrame = null;
    notifyListeners();
  }

  void clearFrame() {
    _latestFrame = null;
    _latestSummary = null;
    _sessionMessage = null;
    notifyListeners();
  }

  void applyProtocolError(Object error) {
    _errorMessage = 'Bad message from backend: $error';
    _clientStatusReason = StatusReasons.protocolError;
    notifyListeners();
  }

  void _onMessage(dynamic raw) {
    try {
      final text = raw is String ? raw : raw.toString();
      final json = jsonDecode(text) as Map<String, dynamic>;
      _clientStatusReason = null;
      final type = json['type'] as String? ?? '';

      switch (type) {
        case 'frame':
          _latestFrame = FrameEventData.fromJson(json);
          notifyListeners();
        case 'session_summary':
          _latestSummary = SessionSummaryData.fromJson(json);
          if (_stopCompleter != null && !_stopCompleter!.isCompleted) {
            _stopCompleter!.complete(_latestSummary);
          }
          notifyListeners();
        case 'session_started':
          _sessionMessage = json['message'] as String?;
          notifyListeners();
        case 'session_cancelled':
          _sessionMessage = 'Session cancelled';
          _latestFrame = null;
          notifyListeners();
        case 'error':
          _errorMessage = json['message'] as String? ?? 'Backend error';
          notifyListeners();
        default:
          break;
      }
    } catch (e) {
      applyProtocolError(e);
    }
  }

  void _setClientStatusReason(String? reason) {
    if (_clientStatusReason == reason) return;
    _clientStatusReason = reason;
    notifyListeners();
  }

  void _setState(WsConnectionState state, {bool clearError = false}) {
    _state = state;
    if (clearError) _errorMessage = null;
    notifyListeners();
  }

  @override
  void dispose() {
    _summaryTimeout?.cancel();
    unawaited(disconnect());
    super.dispose();
  }
}

```
## FILE: lib\features\practice\practice_safety.dart
```
import 'package:flutter/material.dart';

class PracticeSafetyGate {
  const PracticeSafetyGate._();

  static bool _suppressedThisLaunch = false;

  static bool get suppressedThisLaunch => _suppressedThisLaunch;

  static void suppressForLaunch() => _suppressedThisLaunch = true;

  @visibleForTesting
  static void resetForTests() => _suppressedThisLaunch = false;

  static Future<void> showIfNeeded(BuildContext context) async {
    if (_suppressedThisLaunch) return;

    await showModalBottomSheet<void>(
      context: context,
      isDismissible: true,
      enableDrag: true,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (sheetContext) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Practice safely',
                style: Theme.of(sheetContext).textTheme.titleLarge,
              ),
              const SizedBox(height: 12),
              const Text(
                'Use one user and one opaque plastic practice bottle—never '
                'glass. Face a stable, front-facing camera with your full body '
                'visible, good lighting, and a clear practice area. Avoid '
                'advanced tosses near people or breakable objects, and stop if '
                'you feel pain.',
              ),
              const SizedBox(height: 20),
              FilledButton(
                onPressed: () => Navigator.of(sheetContext).pop(),
                child: const Text('I understand — continue'),
              ),
              const SizedBox(height: 8),
              TextButton(
                onPressed: () {
                  suppressForLaunch();
                  Navigator.of(sheetContext).pop();
                },
                child: const Text('Don’t show again this launch'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

```
## FILE: lib\features\practice\practice_shell_screen.dart
```
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/constants/app_constants.dart';
import '../../core/constants/movement_catalog.dart';
import '../../core/constants/status_reasons.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/primary_button.dart';
import '../../core/widgets/status_chip.dart';
import '../../data/models/session_check.dart';
import '../../services/auth_service.dart';
import '../../services/practice_service.dart';
import '../../services/session_service.dart';
import '../../services/websocket_service.dart';
import 'practice_safety.dart';

class PracticeShellScreen extends StatefulWidget {
  const PracticeShellScreen({super.key, required this.movementId});

  final String movementId;

  @override
  State<PracticeShellScreen> createState() => _PracticeShellScreenState();
}

class _PracticeShellScreenState extends State<PracticeShellScreen> {
  Timer? _timer;
  int _elapsed = 0;
  bool _running = false;
  bool _busy = false;
  String? _localError;
  bool _useOfflineMock = false;
  WebSocketService? _ws;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _ws ??= context.read<WebSocketService>();
  }

  @override
  void dispose() {
    _timer?.cancel();
    final ws = _ws;
    if (ws != null && ws.isConnected) {
      ws.cancelSession();
      unawaited(ws.disconnect());
    }
    super.dispose();
  }

  Future<void> _start() async {
    await PracticeSafetyGate.showIfNeeded(context);
    if (!mounted) return;

    setState(() {
      _busy = true;
      _localError = null;
      _useOfflineMock = false;
      _elapsed = 0;
    });

    final ws = context.read<WebSocketService>();
    final auth = context.read<AuthService>();
    final healthy = await ws.checkHealth();
    if (!mounted) return;

    if (!healthy) {
      setState(() {
        _useOfflineMock = true;
        _running = true;
        _busy = false;
        _localError = 'Demo fallback — checkpoints are simulated, not live CV.';
      });
      _timer = Timer.periodic(const Duration(seconds: 1), (_) {
        setState(() => _elapsed++);
      });
      return;
    }

    await ws.connect();
    if (!mounted) return;

    if (!ws.isConnected) {
      setState(() {
        _busy = false;
        _localError = ws.errorMessage ?? 'Could not connect to backend.';
      });
      return;
    }

    ws.startSession(
      movementId: widget.movementId,
      dominantHand:
          auth.currentUser?.dominantHand ?? AppConstants.dominantHandRight,
    );

    setState(() {
      _running = true;
      _busy = false;
    });
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      setState(() => _elapsed++);
    });
  }

  Future<void> _stop() async {
    _timer?.cancel();
    setState(() {
      _running = false;
      _busy = true;
    });

    final sessionService = context.read<SessionService>();
    final ws = context.read<WebSocketService>();

    if (_useOfflineMock) {
      final session = await sessionService.saveMockSession(
        movementId: widget.movementId,
        durationSeconds: _elapsed,
      );
      if (mounted) {
        setState(() => _busy = false);
        context.go('/session-summary/${session.id}');
      }
      return;
    }

    final summary = await ws.stopSession();
    await ws.disconnect();

    if (!mounted) return;

    if (summary == null) {
      setState(() {
        _busy = false;
        _localError = 'No session summary received from backend.';
      });
      return;
    }

    final checks = summary.checks
        .map(
          (c) => SessionCheck(
            id: 0,
            sessionId: 0,
            checkpointKey: c.key,
            checkpointLabel: c.label,
            resultStatus: c.uiStatus,
            measuredValue: c.measuredValue,
            expectedRange: c.expectedRange,
            message: c.message,
            createdAt: DateTime.now(),
          ),
        )
        .toList();

    final session = await sessionService.saveBackendSession(
      movementId: summary.movementId.isEmpty
          ? widget.movementId
          : summary.movementId,
      resultStatus: summary.resultStatus,
      durationSeconds: summary.durationSeconds > 0
          ? summary.durationSeconds
          : _elapsed,
      attemptCount: summary.attemptCount,
      passedCheckCount: summary.passedCheckCount,
      failedCheckCount: summary.failedCheckCount,
      notAssessedCount: summary.notAssessedCount,
      detectionInterruptions: summary.detectionInterruptions,
      assessmentVersion: summary.assessmentVersion,
      checks: checks,
    );

    if (mounted) {
      setState(() => _busy = false);
      context.go('/session-summary/${session.id}');
    }
  }

  String _formatTime(int seconds) {
    final m = seconds ~/ 60;
    final s = seconds % 60;
    return '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final movement = MovementCatalog.findById(widget.movementId);
    final ws = context.watch<WebSocketService>();
    final frame = ws.latestFrame;
    final resolvedBanner = resolveStatusBanner(
      assessmentState: frame?.assessmentState,
      statusReason: frame?.statusReason,
      statusMessage: frame?.statusMessage,
      clientStatusReason: ws.clientStatusReason,
    );
    final banner = _useOfflineMock
        ? const StatusBannerInfo(
            message: 'Demo fallback — checkpoints are simulated, not live CV.',
            tone: StatusBannerTone.warning,
          )
        : _localError != null
        ? StatusBannerInfo(message: _localError!, tone: StatusBannerTone.error)
        : resolvedBanner ??
              (ws.errorMessage != null
                  ? StatusBannerInfo(
                      message: ws.errorMessage!,
                      tone: StatusBannerTone.error,
                    )
                  : ws.sessionMessage != null
                  ? StatusBannerInfo(
                      message: ws.sessionMessage!,
                      tone: StatusBannerTone.warning,
                    )
                  : null);
    final assessmentPaused = frame?.assessmentState == 'unable_to_assess';

    final offlineCheckpoints = context
        .read<PracticeService>()
        .getMockCheckpoints(widget.movementId);

    return Scaffold(
      appBar: AppBar(
        title: Text(movement?.name ?? 'Practice'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: _busy
              ? null
              : () async {
                  if (_running && !_useOfflineMock) {
                    await ws.cancelSession();
                    await ws.disconnect();
                  }
                  if (context.mounted) context.go('/movements');
                },
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 200),
              child: banner == null
                  ? const SizedBox.shrink(key: ValueKey('no-banner'))
                  : _PracticeBanner(
                      key: ValueKey('${banner.tone}:${banner.message}'),
                      info: banner,
                    ),
            ),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  flex: 3,
                  child: Column(
                    children: [
                      Text(
                        _formatTime(_elapsed),
                        style: Theme.of(context).textTheme.displayMedium
                            ?.copyWith(
                              color: AppColors.primary,
                              fontFeatures: const [
                                FontFeature.tabularFigures(),
                              ],
                            ),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 12),
                      AspectRatio(
                        aspectRatio: 4 / 3,
                        child: Container(
                          decoration: BoxDecoration(
                            color: AppColors.card,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: AppColors.textSecondary.withValues(
                                alpha: 0.2,
                              ),
                            ),
                          ),
                          clipBehavior: Clip.antiAlias,
                          child: !_useOfflineMock && frame?.frameBytes != null
                              ? Image.memory(
                                  frame!.frameBytes!,
                                  fit: BoxFit.contain,
                                  gaplessPlayback: true,
                                )
                              : Center(
                                  child: Text(
                                    _running
                                        ? (_useOfflineMock
                                              ? 'Offline practice (no frames)'
                                              : 'Waiting for frames…')
                                        : 'Press Start to connect',
                                    style: Theme.of(
                                      context,
                                    ).textTheme.bodySmall,
                                  ),
                                ),
                        ),
                      ),
                      if (frame != null && !_useOfflineMock) ...[
                        const SizedBox(height: 8),
                        Text(
                          '${frame.assessmentState} · ${frame.currentStep}'
                          ' · conf ${frame.trackingConfidence.toStringAsFixed(2)}',
                          style: Theme.of(context).textTheme.bodySmall,
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(width: 24),
                Expanded(
                  flex: 2,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        'Checkpoints',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      Expanded(
                        child: ListView(
                          children: _useOfflineMock
                              ? offlineCheckpoints
                                    .map(
                                      (cp) => _CheckpointCard(
                                        label: cp.label,
                                        status: cp.status,
                                        message: cp.message,
                                        badge: 'MOCK',
                                        animateStatus: true,
                                      ),
                                    )
                                    .toList()
                              : (frame?.checks ?? const [])
                                    .map(
                                      (cp) => _CheckpointCard(
                                        label: cp.label,
                                        status: cp.uiStatus,
                                        message: cp.message,
                                        badge: 'LIVE',
                                        animateStatus: !assessmentPaused,
                                      ),
                                    )
                                    .toList(),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (!_running)
              Semantics(
                button: true,
                enabled: !_busy,
                label: _busy
                    ? 'Connecting practice session'
                    : 'Start practice session',
                excludeSemantics: true,
                child: PrimaryButton(
                  label: _busy ? 'Connecting…' : 'Start Session',
                  onPressed: _busy ? null : _start,
                ),
              )
            else
              Semantics(
                button: true,
                enabled: !_busy,
                label: _busy
                    ? 'Saving practice session'
                    : 'Stop practice session',
                excludeSemantics: true,
                child: PrimaryButton(
                  label: _busy ? 'Saving…' : 'Stop Session',
                  onPressed: _busy ? null : _stop,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _PracticeBanner extends StatelessWidget {
  const _PracticeBanner({super.key, required this.info});

  final StatusBannerInfo info;

  Color get _color => switch (info.tone) {
    StatusBannerTone.success => AppColors.success,
    StatusBannerTone.warning => AppColors.warning,
    StatusBannerTone.error => AppColors.error,
  };

  IconData get _icon => switch (info.tone) {
    StatusBannerTone.success => Icons.check_circle_outline,
    StatusBannerTone.warning => Icons.warning_amber_outlined,
    StatusBannerTone.error => Icons.error_outline,
  };

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      child: Container(
        padding: const EdgeInsets.all(12),
        margin: const EdgeInsets.only(bottom: 16),
        decoration: BoxDecoration(
          color: _color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: _color.withValues(alpha: 0.4)),
        ),
        child: Row(
          children: [
            Icon(_icon, color: _color, size: 20),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                info.message,
                style: TextStyle(color: _color, fontSize: 13),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CheckpointCard extends StatelessWidget {
  const _CheckpointCard({
    required this.label,
    required this.status,
    required this.message,
    required this.badge,
    required this.animateStatus,
  });

  final String label;
  final String status;
  final String message;
  final String badge;
  final bool animateStatus;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    label,
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                ),
                StatusChip(status: status, animate: animateStatus),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 6,
                    vertical: 2,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.secondary.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    badge,
                    style: const TextStyle(
                      fontSize: 10,
                      color: AppColors.secondary,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(message, style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      ),
    );
  }
}

```
## FILE: lib\core\widgets\status_chip.dart
```
import 'package:flutter/material.dart';

import '../constants/app_constants.dart';
import '../theme/app_theme.dart';

class StatusChip extends StatelessWidget {
  const StatusChip({super.key, required this.status, this.animate = true});

  final String status;
  final bool animate;

  Color get _color {
    switch (status) {
      case AppConstants.resultPassed:
        return AppColors.success;
      case AppConstants.resultFailed:
        return AppColors.error;
      case AppConstants.resultPartial:
        return AppColors.warning;
      case AppConstants.resultNotAssessed:
        return AppColors.textSecondary;
      case AppConstants.resultInProgress:
        return AppColors.secondary;
      default:
        return AppColors.textSecondary;
    }
  }

  String get _label {
    switch (status) {
      case AppConstants.resultPassed:
        return 'Passed';
      case AppConstants.resultFailed:
        return 'Failed';
      case AppConstants.resultPartial:
        return 'Partial';
      case AppConstants.resultNotAssessed:
        return 'Not assessed';
      case AppConstants.resultInProgress:
        return 'In progress';
      default:
        return status;
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedSwitcher(
      duration: animate ? const Duration(milliseconds: 200) : Duration.zero,
      child: Container(
        key: ValueKey(status),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: _color.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: _color.withValues(alpha: 0.5)),
        ),
        child: Text(
          _label,
          style: TextStyle(
            color: _color,
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }
}

```
## FILE: README.md
```
# ELIXR — Windows Desktop Practice Assistant

ELIXR is a local Windows desktop app for beginner flairtending practice. Flutter provides the UI and SQLite session history; a local Python FastAPI backend owns the webcam and runs live computer-vision assessment over WebSocket.

**Default mode:** live CV assessment when the backend is running. Offline or mock paths are developer/demo fallbacks only — not the primary assessment mode.

## Prerequisites

| Component | Requirement |
|---|---|
| OS | Windows 10/11 (desktop target) |
| Flutter | Stable channel with Windows desktop enabled (`flutter doctor`) |
| Python | 3.10+ recommended |
| Hardware | Webcam; opaque plastic practice bottle; front-facing, well-lit setup |

## Quick start

### 1. Backend

```powershell
cd backend
python -m venv C:\elixr-venv
C:\elixr-venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

Verify readiness:

```text
GET http://127.0.0.1:8000/health
```

### 2. Flutter app

In a second terminal, from the repo root:

```powershell
flutter pub get
flutter run -d windows
```

Log in or register, complete onboarding, then use **Camera Test** or **Practice** with the backend running.

### 3. Endpoints (defaults)

Defined in `lib/core/constants/websocket_constants.dart`:

| Endpoint | URL |
|---|---|
| Health | `http://127.0.0.1:8000/health` |
| WebSocket | `ws://127.0.0.1:8000/ws` |

The Flutter client uses these defaults on localhost. Change host/port only if you also update the backend bind address and constants together.

## Camera and session notes

- Only the Python backend opens the webcam during an active session.
- One user, front-facing, full required body region visible, stable camera, good lighting, opaque plastic bottle (no glass).
- Stop or leave practice to release the camera before another app uses it.
- Session results use **checkpoint statuses** and session summary counts (`passed_check_count`, `failed_check_count`, `not_assessed_count`, `result_status`) — not skill percentages.

## Troubleshooting

| Symptom | Likely cause | What to try |
|---|---|---|
| Camera busy / cannot open | Another app holds the webcam | Close other camera apps; Stop practice; restart backend |
| `models_unavailable` | YOLO/MediaPipe failed to load | Re-run `pip install -r requirements.txt`; check backend console for weight/download errors |
| `camera_read_failed` | USB disconnect or driver glitch | Reconnect camera; Stop and Start a new session |
| `backend_disconnected` banner | Backend stopped or wrong port | Start uvicorn on `127.0.0.1:8000`; confirm `/health` responds |
| `low_tracking_confidence` / unable to assess | Body/bottle not stable in frame | Improve lighting; stand front-on; use opaque bottle; reduce motion blur |
| No new passes while unable | Expected Phase 5 behavior | Fix tracking; wait for recovery — prior **passed** checkpoints are preserved |
| Practice shows demo fallback UI | Backend unreachable | Start backend for live CV; fallback is labeled demo, not validated assessment |

Backend unit tests:

```powershell
cd backend
python -m unittest discover -s tests -p "test_*.py" -v
```

Flutter tests:

```powershell
flutter test
```

## Phase documentation

| Doc | Contents |
|---|---|
| [backend/README_PHASE0.md](backend/README_PHASE0.md) | Scope proof / POC |
| [backend/README_PHASE2.md](backend/README_PHASE2.md) | WebSocket protocol |
| [backend/README_PHASE3.md](backend/README_PHASE3.md) | Live CV movements |
| [backend/README_PHASE4.md](backend/README_PHASE4.md) | Persistence + evaluation scripts |
| [backend/README_PHASE5.md](backend/README_PHASE5.md) | Confidence gate, claims tiers, demo stability checklist |
| [backend/assessment/LIMITATIONS.md](backend/assessment/LIMITATIONS.md) | Movement and CV limitations |
| [backend/eval/](backend/eval/) | Bottle detection, expert agreement, FPS/latency, export |

## Developer fallback (not primary assessment)

For UI work without models or camera:

```powershell
set ELIXR_USE_MOCK=1
uvicorn main:app --host 127.0.0.1 --port 8000
```

The Flutter practice shell may also show a labeled offline mock when the backend is unreachable. Do **not** treat either path as validated assessment in demos or manuscript claims.

```
## FILE: backend\README_PHASE5.md
```
# ELIXR Phase 5 — Polish, Documentation, and Demo Readiness

Phase 5 adds low-confidence gating, `status_reason` / `status_message` on frame events, UI polish, soft safety reminders, and in-repo manuscript claim tiers plus a **10-minute demo stability check**.

**Language:** Use **checkpoint statuses** and **session result metrics** (`passed_check_count`, `failed_check_count`, `not_assessed_count`, `result_status`). Do not describe freezing “scores” or skill percentages.

---

## Tracking confidence (composite)

Computed each frame in `LiveAssessmentSession.next_frame_event` via `compute_tracking_confidence` (`assessment/tracking_confidence.py`):

| Signal | Contribution |
|---|---|
| Body landmarks present | `+0.5` |
| Bottle detected (this frame or last YOLO hold) | `+0.4` |
| Session calibration completed | `+0.1` |
| **Total** | Clamped to `[0.0, 1.0]` |

This is a **session readiness / tracking composite**, not YOLO class confidence alone and not MediaPipe landmark visibility average. Camera-test frames use the same formula (calibration term is usually `0` until calibration runs). YOLO per-detection confidence remains on bottle checks via `measured_value` where applicable.

Low-confidence gate compares this composite to `MIN_TRACKING_CONFIDENCE`.

---

## `status_reason` enum and priority

**Backend may emit** (`assessment/status_reasons.py`):

```text
camera_unavailable
camera_read_failed
models_unavailable
internal_error
low_tracking_confidence
body_not_visible
bottle_not_visible
```

**Flutter client-only** (never from Python):

```text
backend_disconnected
protocol_error
```

When multiple conditions apply on one frame, `pick_status_reason` emits the **highest-priority** reason only:

1. `camera_unavailable`
2. `camera_read_failed`
3. `models_unavailable`
4. `internal_error`
5. `low_tracking_confidence` (after debounce latch)
6. `body_not_visible`
7. `bottle_not_visible`

Lower-priority signals may still appear in checkpoint messages; they must not override a higher `status_reason`.

| Condition | `status_reason` | Message guidance |
|---|---|---|
| Camera cannot open | `camera_unavailable` | Webcam busy or wrong index; close other apps |
| Frame read failed | `camera_read_failed` | Camera disconnected; reconnect and restart session |
| Pose/YOLO failed to load | `models_unavailable` | Check Python deps / weights |
| Unexpected frame pipeline exception | `internal_error` | Restart session; check backend logs |
| Body missing (after higher priorities) | `body_not_visible` | Stand in frame; front-facing; full body region |
| Bottle missing when required | `bottle_not_visible` | Opaque plastic bottle; improve lighting |

Additive optional FrameEvent fields: `status_reason`, `status_message`. `assessment_state` remains the source of truth.

---

## Config knobs (`config.py`)

| Setting | Default | Role |
|---|---|---|
| `MIN_TRACKING_CONFIDENCE` | `0.45` | Threshold for low-confidence latch |
| `LOW_CONFIDENCE_FRAMES_REQUIRED` | `5` | Consecutive low frames to enter unable |
| `LOW_CONFIDENCE_RECOVERY_FRAMES` | `5` | Consecutive at/above-threshold frames to exit latch |

**Enter latch** (`LowConfidenceGate`): after `LOW_CONFIDENCE_FRAMES_REQUIRED` consecutive frames with `tracking_confidence < MIN_TRACKING_CONFIDENCE`:

- `assessment_state = unable_to_assess`
- `status_reason = low_tracking_confidence` (unless higher priority applies)
- actionable `status_message`

**Exit latch:** after `LOW_CONFIDENCE_RECOVERY_FRAMES` consecutive frames at/above threshold, clear latch and resume normal evaluation.

---

## Freeze and resume while unable

Applies to low-confidence latch **and** hard failures (models/camera/`internal_error`) that set `unable_to_assess`:

1. **Do not call** movement assessor `update()` while latched/unable — freeze internal sequence counters/state.
2. **Preserve** previously `passed` checkpoints in outgoing `checks` (`merge_checks_while_unable`).
3. **Do not emit** new `passed` statuses while unable.
4. Incomplete keys surface as `not_assessed` or retained `in_progress` without promoting to `passed`.

| Event | Behavior |
|---|---|
| Low-confidence enter | Freeze assessor; keep prior `passed` checks; `assessment_state=unable_to_assess` |
| Low-confidence exit (recovery) | **Resume** assessor from frozen state — **no full sequence reset** |
| Models/camera/`internal_error` cleared, session still open | Resume from frozen state when frames become usable |
| User Stop / Cancel / new `start` | Full teardown; **new** session resets calibration + assessor |
| Unexpected practice exit (Flutter dispose) | Cancel + disconnect; backend `close()` releases camera; next Start is new session |

No mid-session auto-reset of a multi-step movement solely because confidence dipped and recovered.

---

## Manuscript claims checklist (four tiers)

Use these tiers in thesis/manuscript materials. Do not claim features in a higher tier unless evidence exists.

| Tier | Meaning | Examples |
|---|---|---|
| **Implemented** | Present in the running app/backend | Local login/register, onboarding, safety content, live WS assessment for enabled movements, SQLite sessions, history/progress, CSV export, soft safety reminder, low-confidence gate, reason codes |
| **Technically tested** | Automated tests or measured scripts with evidence | Unit tests for confidence/debounce/recovery/freeze/priority; bottle/FPS scripts **only where datasets/runs exist** (`backend/eval/`) |
| **User-evaluated** | Usability Likert / participant feedback (not CV ground truth unless experts) | Ease of use, clarity of feedback |
| **Not validated** | Must **not** be claimed as proven | Production accuracy for all movements, grip/rotation/contact, injury prevention, cloud deploy, `.exe` packaging, skill percentages, offline mock as validated assessment |

**Mock copy rule:** Default narrative is **live CV when backend is running**. Flutter offline mock and `ELIXR_USE_MOCK=1` are dev/demo fallbacks — do not list them under **Implemented** as primary assessment or under **Technically tested** without explicit labeled-demo evidence.

---

## 10-minute demo stability check

**Label:** short **demo stability check** (manual, reference laptop) — **not** a formal soak test.

Fill the environment block at run time before claiming “tested on reference hardware.”

### Tested environment (fill at run time)

| Field | Value |
|---|---|
| OS build | |
| Laptop model / CPU / RAM | |
| Camera model / index | |
| Flutter channel / version | |
| Python version | |
| Backend command | `uvicorn main:app --host 127.0.0.1 --port 8000` |
| Lighting notes | |
| Practice bottle description | |

### Checklist

| # | Check | Pass condition |
|---|---|---|
| 1 | Camera release after Stop / leave practice | Next Start opens camera; no “busy device” without closing other apps |
| 2 | No duplicate WebSocket on Start | Single active connection; no double frame streams or duplicate session summaries |
| 3 | Memory over ~10 minutes | No multi‑GB RAM climb; growth bounded during continuous practice |
| 4 | UI responsiveness | No sustained freeze **> 2 s** during normal use |
| 5 | One Stop → one session save | Exactly one summary persisted per completed Stop (no duplicate rows for one stop) |
| 6 | No false-pass while unable | No **new** `passed` checkpoints during `unable_to_assess` / low-confidence latch |
| 7 | Unexpected practice exit | Navigate away or close practice without Stop → camera released; backend session cleaned up |
| 8 | Optional: backend stop mid-session | Flutter shows actionable `backend_disconnected` banner |

### Practical pass (all required)

- No crash during the 10-minute window
- Single summary save per intentional Stop
- Camera reopens on next Start
- No sustained UI freeze (> 2 s)
- No new passes while unable
- No multi‑GB RAM climb over 10 minutes

Record pass/fail and notes in your demo log; attach environment table when citing stability in manuscript materials.

---

## Run and tests

Same as Phase 3/4:

```powershell
cd backend
C:\elixr-venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

```powershell
flutter run -d windows
```

Phase 5 backend tests:

```powershell
cd backend
python -m unittest discover -s tests -p "test_phase5*.py" -v
```

See also [LIMITATIONS.md](assessment/LIMITATIONS.md) and root [README.md](../README.md).

```

