"""Live CV assessment session for WebSocket (Phase 3)."""

from __future__ import annotations

import base64
import os
import threading
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
        self._latest_bgr: Optional[np.ndarray] = None
        self._capture_lock = threading.Lock()
        self._capture_stop: Optional[threading.Event] = None
        self._capture_thread: Optional[threading.Thread] = None
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
        self._stop_capture()
        try:
            cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap.release()
                cap = cv2.VideoCapture(self.camera_index)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
                # Prefer a tiny driver buffer so read() does not serve stale frames.
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self._cap = cap
                self.camera_source = "webcam"
                self._camera_failure_reason = None
                self._start_capture()
            else:
                cap.release()
                self._camera_failure_reason = CAMERA_UNAVAILABLE
                self.detection_interruptions += 1
        except Exception:
            self._cap = None
            self.camera_source = "placeholder"
            self._camera_failure_reason = CAMERA_UNAVAILABLE
            self.detection_interruptions += 1

    def _start_capture(self) -> None:
        """Continuously grab frames, keeping only the newest (drops backlog lag)."""
        self._stop_capture()
        self._latest_bgr = None
        self._capture_stop = threading.Event()
        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            name="elixr-camera",
            daemon=True,
        )
        self._capture_thread.start()

    def _stop_capture(self) -> None:
        stop = getattr(self, "_capture_stop", None)
        thread = getattr(self, "_capture_thread", None)
        if stop is not None:
            stop.set()
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)
        self._capture_thread = None
        self._capture_stop = None
        lock = getattr(self, "_capture_lock", None)
        if lock is not None:
            with lock:
                self._latest_bgr = None
        else:
            self._latest_bgr = None

    def _capture_loop(self) -> None:
        stop = self._capture_stop
        if stop is None:
            return
        while not stop.is_set():
            cap = self._cap
            if cap is None:
                break
            ok, frame = cap.read()
            if not ok or frame is None:
                with self._capture_lock:
                    self._latest_bgr = None
                # Brief pause so a disconnected camera does not spin the CPU.
                stop.wait(0.02)
                continue
            with self._capture_lock:
                # Overwrite — never queue. Assessment always sees "now".
                self._latest_bgr = frame

    def _release_camera(self) -> None:
        self._stop_capture()
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
            frame: Optional[np.ndarray] = None
            lock = getattr(self, "_capture_lock", None)
            if lock is not None:
                with lock:
                    if getattr(self, "_latest_bgr", None) is not None:
                        frame = self._latest_bgr.copy()
            if frame is None:
                # Startup race, capture stall, or tests without capture thread.
                ok, direct = self._cap.read()
                if ok and direct is not None:
                    frame = direct
                else:
                    self._release_camera()
                    self.camera_source = "placeholder"
                    self._camera_failure_reason = CAMERA_READ_FAILED
                    self.detection_interruptions += 1
                    return self._build_placeholder(
                        "Webcam unavailable — placeholder frame"
                    )
            if self.mirror_camera:
                frame = cv2.flip(frame, 1)
            return cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
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
