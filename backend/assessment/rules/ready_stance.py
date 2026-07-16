"""Ready Stance — full-body framing and stance hold."""

from __future__ import annotations

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
    shoulder_level_norm,
    stance_width_norm,
    torso_centered,
)
from assessment.movement_state import CheckResult, State, TERMINAL_STATES
from config import (
    HOLD_FRAMES_REQUIRED,
    SHOULDER_LEVEL_MAX_NORM,
    START_FRAMES_REQUIRED,
    STANCE_WIDTH_MAX,
    STANCE_WIDTH_MIN,
)
from vision.bottle_detector import BottleBox
from vision.pose_detector import Landmark


@dataclass
class ReadyStanceAssessor:
    calibration: Calibration
    state: State = State.NOT_READY
    start_frames: int = 0
    hold_frames: int = 0
    checks: list[CheckResult] = field(default_factory=list)
    requires_bottle: bool = False

    def _pose_ok(self, landmarks: dict[str, Landmark]) -> bool:
        if not required_visible(landmarks, REQUIRED_FULL_BODY):
            return False
        centered, _ = torso_centered(landmarks)
        sw = stance_width_norm(landmarks, self.calibration.shoulder_width)
        level = shoulder_level_norm(landmarks, self.calibration.shoulder_width)
        if sw is None or level is None:
            return False
        return (
            centered
            and STANCE_WIDTH_MIN <= sw <= STANCE_WIDTH_MAX
            and level <= SHOULDER_LEVEL_MAX_NORM
        )

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

        ok = self._pose_ok(landmarks)

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
            if ok:
                self.hold_frames += 1
            else:
                self.hold_frames = max(0, self.hold_frames - 1)
            if self.hold_frames >= HOLD_FRAMES_REQUIRED:
                self.checks = [
                    check_body_visibility(landmarks),
                    check_torso_center(landmarks),
                    check_stance_width(landmarks, self.calibration.shoulder_width),
                    check_shoulder_level(landmarks, self.calibration.shoulder_width),
                    CheckResult(
                        "hold_duration",
                        "Stance hold",
                        "passed",
                        f"Held ready stance for {HOLD_FRAMES_REQUIRED} frames.",
                        measured_value=float(HOLD_FRAMES_REQUIRED),
                        expected_range=f">= {HOLD_FRAMES_REQUIRED} frames",
                    ),
                ]
                self.state = finalize_status(self.checks)
            return self.state

        return self.state
