"""Basic Bottle Hold Position — bottle near wrist at expected height."""

from __future__ import annotations

from dataclasses import dataclass, field

from assessment.calibration import Calibration
from assessment.checks import (
    arm_landmarks,
    bottle_wrist_distance_norm,
    check_bottle_visibility,
    check_bottle_wrist,
    finalize_status,
)
from assessment.movement_state import CheckResult, State, TERMINAL_STATES
from config import (
    BOTTLE_WRIST_MAX_NORM,
    HOLD_FRAMES_REQUIRED,
    START_FRAMES_REQUIRED,
    WAIST_Y_MAX,
    WAIST_Y_MIN,
)
from vision.bottle_detector import BottleBox
from vision.pose_detector import Landmark


@dataclass
class BasicBottleHoldAssessor:
    calibration: Calibration
    state: State = State.NOT_READY
    start_frames: int = 0
    hold_frames: int = 0
    checks: list[CheckResult] = field(default_factory=list)
    requires_bottle: bool = True

    def _side(self) -> str:
        return "right" if self.calibration.dominant_hand == "right" else "left"

    def update(
        self,
        landmarks: dict[str, Landmark] | None,
        bottle: BottleBox | None,
        frame_w: int,
        frame_h: int,
    ) -> State:
        if self.state in TERMINAL_STATES:
            return self.state

        if landmarks is None:
            self.state = State.UNABLE_TO_ASSESS
            self.checks = [
                CheckResult(
                    "body_visibility",
                    "Body visibility",
                    "not_assessed",
                    "Pose landmarks not visible.",
                )
            ]
            return self.state

        arm = arm_landmarks(landmarks, self._side())
        if arm is None:
            self.state = State.UNABLE_TO_ASSESS
            self.checks = [
                CheckResult(
                    "body_visibility",
                    "Body visibility",
                    "not_assessed",
                    "Dominant arm landmarks missing.",
                )
            ]
            return self.state

        _, _, wrist = arm
        bottle_dist = bottle_wrist_distance_norm(
            bottle, wrist, self.calibration.shoulder_width, frame_w, frame_h
        )
        bottle_near = bottle_dist is not None and bottle_dist <= BOTTLE_WRIST_MAX_NORM
        height_ok = WAIST_Y_MIN <= wrist.y <= WAIST_Y_MAX
        pose_ok = bottle is not None and bottle_near and height_ok

        if self.state == State.UNABLE_TO_ASSESS:
            self.state = State.NOT_READY

        if self.state == State.NOT_READY:
            self.start_frames = self.start_frames + 1 if pose_ok else 0
            if self.start_frames >= START_FRAMES_REQUIRED:
                self.state = State.START_POSITION
            return self.state

        if self.state == State.START_POSITION:
            self.state = State.HOLD_CONFIRMATION
            self.hold_frames = 0

        if self.state == State.HOLD_CONFIRMATION:
            if pose_ok:
                self.hold_frames += 1
            else:
                self.hold_frames = max(0, self.hold_frames - 1)
            if self.hold_frames >= HOLD_FRAMES_REQUIRED:
                self.checks = [
                    check_bottle_visibility(bottle),
                    check_bottle_wrist(
                        bottle,
                        wrist,
                        self.calibration.shoulder_width,
                        frame_w,
                        frame_h,
                    ),
                    CheckResult(
                        "hold_height",
                        "Starting hold height",
                        "passed" if height_ok else "needs_improvement",
                        "Bottle/wrist height in expected range."
                        if height_ok
                        else "Hold the bottle near waist height.",
                        measured_value=round(wrist.y, 3),
                        expected_range=f"y in [{WAIST_Y_MIN}, {WAIST_Y_MAX}]",
                    ),
                    CheckResult(
                        "hold_duration",
                        "Hold duration",
                        "passed",
                        f"Held for {HOLD_FRAMES_REQUIRED} frames.",
                        measured_value=float(HOLD_FRAMES_REQUIRED),
                        expected_range=f">= {HOLD_FRAMES_REQUIRED} frames",
                    ),
                ]
                self.state = finalize_status(self.checks)
            return self.state

        return self.state
