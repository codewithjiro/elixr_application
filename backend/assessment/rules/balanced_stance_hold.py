"""Balanced Stance Hold — longer hold with low torso/ankle jitter."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from assessment.calibration import Calibration
from assessment.checks import (
    REQUIRED_FULL_BODY,
    check_body_visibility,
    check_shoulder_level,
    check_stance_width,
    check_torso_center,
    finalize_status,
    required_visible,
    stance_width_norm,
    torso_centered,
)
from assessment.movement_state import CheckResult, State, TERMINAL_STATES
from config import (
    LONG_HOLD_FRAMES_REQUIRED,
    START_FRAMES_REQUIRED,
    STABILITY_JITTER_MAX,
    STANCE_WIDTH_MAX,
    STANCE_WIDTH_MIN,
)
from vision import geometry
from vision.bottle_detector import BottleBox
from vision.pose_detector import Landmark


@dataclass
class BalancedStanceHoldAssessor:
    calibration: Calibration
    state: State = State.NOT_READY
    start_frames: int = 0
    hold_frames: int = 0
    checks: list[CheckResult] = field(default_factory=list)
    requires_bottle: bool = False
    _centers: deque[tuple[float, float]] = field(
        default_factory=lambda: deque(maxlen=20)
    )

    def _jitter(self) -> float | None:
        if len(self._centers) < 5:
            return None
        xs = [c[0] for c in self._centers]
        ys = [c[1] for c in self._centers]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        # mean absolute deviation / shoulder width
        mad = sum(abs(x - mx) + abs(y - my) for x, y in self._centers) / len(
            self._centers
        )
        return mad / self.calibration.shoulder_width

    def _pose_ok(self, landmarks: dict[str, Landmark]) -> bool:
        if not required_visible(landmarks, REQUIRED_FULL_BODY):
            return False
        centered, _ = torso_centered(landmarks)
        sw = stance_width_norm(landmarks, self.calibration.shoulder_width)
        if sw is None:
            return False
        return centered and STANCE_WIDTH_MIN <= sw <= STANCE_WIDTH_MAX

    def update(
        self,
        landmarks: dict[str, Landmark] | None,
        bottle: BottleBox | None,
        frame_w: int,
        frame_h: int,
    ) -> State:
        del bottle, frame_w, frame_h
        if self.state in TERMINAL_STATES:
            return self.state

        if landmarks is None or not required_visible(landmarks, REQUIRED_FULL_BODY):
            self.state = State.UNABLE_TO_ASSESS
            self.checks = [
                CheckResult(
                    "body_visibility",
                    "Body visibility",
                    "not_assessed",
                    "Full body not visible.",
                )
            ]
            return self.state

        tc = geometry.torso_center(landmarks)
        if tc is not None:
            self._centers.append(tc)

        ok = self._pose_ok(landmarks)
        jitter = self._jitter()
        stable = jitter is not None and jitter <= STABILITY_JITTER_MAX

        if self.state == State.UNABLE_TO_ASSESS:
            self.state = State.NOT_READY

        if self.state == State.NOT_READY:
            self.start_frames = self.start_frames + 1 if ok else 0
            if self.start_frames >= START_FRAMES_REQUIRED:
                self.state = State.START_POSITION
            return self.state

        if self.state == State.START_POSITION:
            self.state = State.HOLD_CONFIRMATION
            self.hold_frames = 0

        if self.state == State.HOLD_CONFIRMATION:
            if ok and (jitter is None or stable):
                self.hold_frames += 1
            else:
                self.hold_frames = max(0, self.hold_frames - 1)

            if self.hold_frames >= LONG_HOLD_FRAMES_REQUIRED:
                jit_status = "not_assessed" if jitter is None else (
                    "passed" if stable else "needs_improvement"
                )
                self.checks = [
                    check_body_visibility(landmarks),
                    check_torso_center(landmarks),
                    check_stance_width(landmarks, self.calibration.shoulder_width),
                    check_shoulder_level(landmarks, self.calibration.shoulder_width),
                    CheckResult(
                        "stability",
                        "Stance stability",
                        jit_status,
                        "Hold still with limited sway."
                        if jit_status != "passed"
                        else "Stance remained stable.",
                        measured_value=None if jitter is None else round(jitter, 4),
                        expected_range=f"<= {STABILITY_JITTER_MAX}",
                    ),
                    CheckResult(
                        "hold_duration",
                        "Balanced hold",
                        "passed",
                        f"Held for {LONG_HOLD_FRAMES_REQUIRED} frames.",
                        measured_value=float(LONG_HOLD_FRAMES_REQUIRED),
                        expected_range=f">= {LONG_HOLD_FRAMES_REQUIRED} frames",
                    ),
                ]
                self.state = finalize_status(self.checks)
            return self.state

        return self.state
