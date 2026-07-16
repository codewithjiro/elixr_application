"""Controlled Bottle Lowering — downward path back toward start height."""

from __future__ import annotations

from dataclasses import dataclass, field

from assessment.calibration import Calibration
from assessment.checks import (
    arm_landmarks,
    bottle_wrist_distance_norm,
    check_bottle_wrist,
    finalize_status,
)
from assessment.movement_state import CheckResult, State, TERMINAL_STATES
from config import (
    BOTTLE_WRIST_MAX_NORM,
    HOLD_FRAMES_REQUIRED,
    LOWERING_START_Y_MAX,
    PATH_MIN_DELTA_Y,
    START_FRAMES_REQUIRED,
    WAIST_Y_MAX,
    WAIST_Y_MIN,
)
from vision.bottle_detector import BottleBox
from vision.pose_detector import Landmark


@dataclass
class ControlledBottleLoweringAssessor:
    calibration: Calibration
    state: State = State.NOT_READY
    start_frames: int = 0
    hold_frames: int = 0
    start_y: float | None = None
    max_y: float | None = None
    path_frames: int = 0
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
        high_start = wrist.y <= LOWERING_START_Y_MAX

        if self.state == State.UNABLE_TO_ASSESS:
            self.state = State.NOT_READY

        if self.state == State.NOT_READY:
            if high_start and bottle_near:
                self.start_frames += 1
            else:
                self.start_frames = 0
            if self.start_frames >= START_FRAMES_REQUIRED:
                self.state = State.START_POSITION
                self.start_y = wrist.y
                self.max_y = wrist.y
                self.path_frames = 0
            return self.state

        if self.state == State.START_POSITION:
            if self.start_y is not None and wrist.y > self.start_y + PATH_MIN_DELTA_Y / 2:
                self.state = State.MOVEMENT_IN_PROGRESS
            return self.state

        if self.state == State.MOVEMENT_IN_PROGRESS:
            self.max_y = max(self.max_y or wrist.y, wrist.y)
            self.path_frames += 1
            returned = WAIST_Y_MIN <= wrist.y <= WAIST_Y_MAX
            if returned and bottle_near:
                self.state = State.END_POSITION
                self.hold_frames = 0
            return self.state

        if self.state in (State.END_POSITION, State.HOLD_CONFIRMATION):
            self.state = State.HOLD_CONFIRMATION
            returned = WAIST_Y_MIN <= wrist.y <= WAIST_Y_MAX
            if returned and bottle_near:
                self.hold_frames += 1
            else:
                self.hold_frames = max(0, self.hold_frames - 1)

            if self.hold_frames >= HOLD_FRAMES_REQUIRED:
                path_ok = (
                    self.start_y is not None
                    and self.max_y is not None
                    and (self.max_y - self.start_y) >= PATH_MIN_DELTA_Y
                )
                # Controlled: not instantaneous — require several path frames
                duration_ok = self.path_frames >= START_FRAMES_REQUIRED
                self.checks = [
                    CheckResult(
                        "high_start",
                        "Elevated start",
                        "passed",
                        "Started from an elevated hold.",
                    ),
                    CheckResult(
                        "downward_path",
                        "Downward path",
                        "passed" if path_ok else "needs_improvement",
                        "Lowered the bottle." if path_ok else "Lower the bottle more clearly.",
                        measured_value=None
                        if self.start_y is None or self.max_y is None
                        else round(self.max_y - self.start_y, 3),
                        expected_range=f">= {PATH_MIN_DELTA_Y}",
                    ),
                    CheckResult(
                        "controlled_duration",
                        "Controlled duration",
                        "passed" if duration_ok else "needs_improvement",
                        "Lowering was paced."
                        if duration_ok
                        else "Lower more slowly / controllably.",
                        measured_value=float(self.path_frames),
                        expected_range=f">= {START_FRAMES_REQUIRED} frames",
                    ),
                    CheckResult(
                        "return_height",
                        "Return height",
                        "passed" if returned else "needs_improvement",
                        "Returned near start/waist height."
                        if returned
                        else "Finish near waist height.",
                        measured_value=round(wrist.y, 3),
                        expected_range=f"y in [{WAIST_Y_MIN}, {WAIST_Y_MAX}]",
                    ),
                    check_bottle_wrist(
                        bottle,
                        wrist,
                        self.calibration.shoulder_width,
                        frame_w,
                        frame_h,
                    ),
                ]
                self.state = finalize_status(self.checks)
            return self.state

        return self.state
