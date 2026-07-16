"""Front Bottle Lift — upward wrist path with limited lean."""

from __future__ import annotations

from dataclasses import dataclass, field

from assessment.calibration import Calibration
from assessment.checks import (
    arm_landmarks,
    bottle_wrist_distance_norm,
    check_bottle_wrist,
    check_torso_lean,
    finalize_status,
)
from assessment.movement_state import CheckResult, State, TERMINAL_STATES
from config import (
    BOTTLE_WRIST_MAX_NORM,
    CHEST_Y_MAX,
    HOLD_FRAMES_REQUIRED,
    PATH_MIN_DELTA_Y,
    START_FRAMES_REQUIRED,
    WAIST_Y_MIN,
)
from vision.bottle_detector import BottleBox
from vision.pose_detector import Landmark


@dataclass
class FrontBottleLiftAssessor:
    calibration: Calibration
    state: State = State.NOT_READY
    start_frames: int = 0
    hold_frames: int = 0
    start_y: float | None = None
    min_y: float | None = None
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
        low_start = wrist.y >= WAIST_Y_MIN

        if self.state == State.UNABLE_TO_ASSESS:
            self.state = State.NOT_READY

        if self.state == State.NOT_READY:
            if low_start and bottle_near:
                self.start_frames += 1
            else:
                self.start_frames = 0
            if self.start_frames >= START_FRAMES_REQUIRED:
                self.state = State.START_POSITION
                self.start_y = wrist.y
                self.min_y = wrist.y
            return self.state

        if self.state == State.START_POSITION:
            self.min_y = min(self.min_y or wrist.y, wrist.y)
            if self.start_y is not None and wrist.y < self.start_y - PATH_MIN_DELTA_Y / 2:
                self.state = State.MOVEMENT_IN_PROGRESS
            return self.state

        if self.state == State.MOVEMENT_IN_PROGRESS:
            self.min_y = min(self.min_y or wrist.y, wrist.y)
            if wrist.y <= CHEST_Y_MAX and bottle_near:
                self.state = State.END_POSITION
                self.hold_frames = 0
            return self.state

        if self.state in (State.END_POSITION, State.HOLD_CONFIRMATION):
            self.state = State.HOLD_CONFIRMATION
            self.min_y = min(self.min_y or wrist.y, wrist.y)
            if wrist.y <= CHEST_Y_MAX and bottle_near:
                self.hold_frames += 1
            else:
                self.hold_frames = max(0, self.hold_frames - 1)

            if self.hold_frames >= HOLD_FRAMES_REQUIRED:
                path_ok = (
                    self.start_y is not None
                    and self.min_y is not None
                    and (self.start_y - self.min_y) >= PATH_MIN_DELTA_Y
                )
                height_ok = wrist.y <= CHEST_Y_MAX
                self.checks = [
                    CheckResult(
                        "start_below_chest",
                        "Start below chest",
                        "passed",
                        "Low start position detected.",
                    ),
                    CheckResult(
                        "upward_path",
                        "Upward wrist path",
                        "passed" if path_ok else "needs_improvement",
                        "Wrist rose enough." if path_ok else "Lift the bottle upward more clearly.",
                        measured_value=None
                        if self.start_y is None or self.min_y is None
                        else round(self.start_y - self.min_y, 3),
                        expected_range=f">= {PATH_MIN_DELTA_Y}",
                    ),
                    CheckResult(
                        "final_height",
                        "Final bottle/wrist height",
                        "passed" if height_ok else "needs_improvement",
                        "Reached chest/shoulder height."
                        if height_ok
                        else "Raise the bottle higher.",
                        measured_value=round(wrist.y, 3),
                        expected_range=f"y <= {CHEST_Y_MAX}",
                    ),
                    check_bottle_wrist(
                        bottle,
                        wrist,
                        self.calibration.shoulder_width,
                        frame_w,
                        frame_h,
                    ),
                    check_torso_lean(landmarks, self.calibration.shoulder_width),
                ]
                self.state = finalize_status(self.checks)
            return self.state

        return self.state
