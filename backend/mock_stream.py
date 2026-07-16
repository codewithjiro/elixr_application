"""Phase 2 mock frame + assessment progression (no real CV scoring yet)."""

from __future__ import annotations

import base64
import time
from typing import Optional

import cv2
import numpy as np

from config import CAMERA_INDEX, FRAME_HEIGHT, FRAME_WIDTH
from schemas.frame_event import CheckpointUpdate, FrameEvent
from schemas.session_result import SessionSummary


class MockAssessmentSession:
    """Streams placeholder/webcam JPEGs with evolving mock checkpoint events."""

    def __init__(
        self,
        movement_id: str,
        dominant_hand: str = "right",
        mirror_camera: bool = True,
        camera_index: int = CAMERA_INDEX,
    ) -> None:
        self.movement_id = movement_id
        self.dominant_hand = dominant_hand
        self.mirror_camera = mirror_camera
        self.camera_index = camera_index
        self.started_at = time.monotonic()
        self.frame_index = 0
        self._cap: Optional[cv2.VideoCapture] = None
        self.camera_source = "placeholder"
        self._open_camera()

    def _open_camera(self) -> None:
        try:
            cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(self.camera_index)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
                self._cap = cap
                self.camera_source = "webcam"
            else:
                cap.release()
        except Exception:
            self._cap = None
            self.camera_source = "placeholder"

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    @property
    def elapsed_seconds(self) -> int:
        return int(time.monotonic() - self.started_at)

    def _build_placeholder(self) -> np.ndarray:
        frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
        frame[:] = (28, 28, 36)
        elapsed = self.elapsed_seconds
        cv2.putText(
            frame,
            "ELIXR Phase 2",
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
            f"Mock stream · {elapsed}s · hand={self.dominant_hand}",
            (24, 140),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (160, 160, 170),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            "Webcam unavailable — placeholder frame",
            (24, FRAME_HEIGHT - 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (251, 191, 36),
            1,
            cv2.LINE_AA,
        )
        # Simple motion bar so Flutter UI clearly updates
        bar_w = int((self.frame_index % 60) / 60 * (FRAME_WIDTH - 48))
        cv2.rectangle(frame, (24, 180), (24 + bar_w, 196), (110, 231, 183), -1)
        return frame

    def _read_frame(self) -> np.ndarray:
        if self._cap is not None:
            ok, frame = self._cap.read()
            if ok and frame is not None:
                if self.mirror_camera:
                    frame = cv2.flip(frame, 1)
                frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
                label = f"MOCK CHECKS · {self.movement_id}"
                cv2.putText(
                    frame,
                    label,
                    (12, 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 77, 141),
                    2,
                    cv2.LINE_AA,
                )
                return frame
            # Camera dropped — fall back
            self.close()
            self.camera_source = "placeholder"
        return self._build_placeholder()

    def _encode_jpeg(self, frame: np.ndarray) -> str:
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if not ok:
            return ""
        return base64.b64encode(buf.tobytes()).decode("ascii")

    def _assessment_progress(self) -> tuple[str, str, list[CheckpointUpdate], bool, bool, float]:
        """Return state, step, checks, body, bottle, confidence."""
        t = self.elapsed_seconds

        # Camera-test mode stays on readiness
        if self.movement_id in ("camera_test", "camera_readiness"):
            return (
                "camera_ready",
                "readiness_check",
                [
                    CheckpointUpdate(
                        key="body_visibility",
                        status="passed" if t > 1 else "not_assessed",
                        message="Body landmarks visible (mock)."
                        if t > 1
                        else "Waiting for body visibility…",
                    ),
                    CheckpointUpdate(
                        key="bottle_visibility",
                        status="passed" if t > 2 else "not_assessed",
                        message="Bottle detected (mock)."
                        if t > 2
                        else "Waiting for bottle…",
                    ),
                ],
                t > 1,
                t > 2,
                0.82 if t > 2 else 0.45,
            )

        if t < 3:
            return (
                "camera_ready",
                "readiness_check",
                [
                    CheckpointUpdate(
                        key="body_visibility",
                        status="in_progress",
                        message="Stand fully in frame.",
                    ),
                    CheckpointUpdate(
                        key="bottle_visibility",
                        status="not_assessed",
                        message="Hold the practice bottle.",
                    ),
                ],
                True,
                False,
                0.55,
            )

        if t < 6:
            return (
                "calibrating",
                "calibration",
                [
                    CheckpointUpdate(
                        key="body_visibility",
                        status="passed",
                        message="Body visible.",
                    ),
                    CheckpointUpdate(
                        key="stance_width",
                        status="in_progress",
                        message="Hold ready stance for calibration.",
                        measured_value=0.95,
                        expected_range="0.85-1.15 shoulder widths",
                    ),
                    CheckpointUpdate(
                        key="bottle_visibility",
                        status="passed",
                        message="Bottle visible (mock).",
                    ),
                ],
                True,
                True,
                0.78,
            )

        if t < 12:
            return (
                "movement_in_progress",
                "extend_arm",
                [
                    CheckpointUpdate(
                        key="elbow_angle",
                        status="needs_improvement",
                        message="Straighten your elbow slightly.",
                        measured_value=148.0,
                        expected_range="160-180 degrees",
                    ),
                    CheckpointUpdate(
                        key="bottle_wrist_proximity",
                        status="passed",
                        message="Bottle near wrist (approximate).",
                        measured_value=0.32,
                        expected_range="<= 0.55 shoulder widths",
                    ),
                    CheckpointUpdate(
                        key="torso_lean",
                        status="passed",
                        message="Torso upright.",
                        measured_value=0.08,
                        expected_range="<= 0.25",
                    ),
                ],
                True,
                True,
                0.84,
            )

        return (
            "movement_hold",
            "hold_extension",
            [
                CheckpointUpdate(
                    key="elbow_angle",
                    status="passed",
                    message="Elbow extended.",
                    measured_value=168.0,
                    expected_range="160-180 degrees",
                ),
                CheckpointUpdate(
                    key="bottle_wrist_proximity",
                    status="passed",
                    message="Bottle near wrist (approximate).",
                    measured_value=0.28,
                    expected_range="<= 0.55 shoulder widths",
                ),
                CheckpointUpdate(
                    key="hold_stability",
                    status="passed" if t >= 15 else "in_progress",
                    message="Hold steady." if t < 15 else "Hold complete (mock).",
                    measured_value=float(min(t - 12, 3)),
                    expected_range="3 seconds",
                ),
            ],
            True,
            True,
            0.90,
        )

    def next_frame_event(self) -> FrameEvent:
        self.frame_index += 1
        frame = self._read_frame()
        jpeg = self._encode_jpeg(frame)
        state, step, checks, body, bottle, conf = self._assessment_progress()
        return FrameEvent(
            movement_id=self.movement_id,
            assessment_state=state,
            body_detected=body,
            bottle_detected=bottle,
            tracking_confidence=conf,
            current_step=step,
            checks=checks,
            frame_jpeg_base64=jpeg,
            camera_source=self.camera_source,
        )

    def build_summary(self) -> SessionSummary:
        _, _, checks, _, _, _ = self._assessment_progress()
        passed = sum(1 for c in checks if c.status == "passed")
        failed = sum(1 for c in checks if c.status in ("failed", "needs_improvement"))
        not_assessed = sum(
            1 for c in checks if c.status in ("not_assessed", "in_progress")
        )
        duration = max(self.elapsed_seconds, 1)
        if passed > 0 and failed == 0 and not_assessed == 0:
            result = "completed"
        elif passed > 0:
            result = "partial"
        else:
            result = "not_assessed"

        return SessionSummary(
            movement_id=self.movement_id,
            result_status=result,
            duration_seconds=duration,
            attempt_count=1,
            passed_check_count=passed,
            failed_check_count=failed,
            not_assessed_count=not_assessed,
            detection_interruptions=0 if self.camera_source == "webcam" else 1,
            assessment_version="2.0-mock",
            checks=checks,
            message="Phase 2 mock assessment — replace with real rules in Phase 3.",
        )
