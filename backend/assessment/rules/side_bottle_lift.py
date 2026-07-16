"""Side Bottle Lift — outward/upward wrist path with limited shoulder hike."""

from __future__ import annotations

from dataclasses import dataclass, field

from assessment.calibration import Calibration
from assessment.checks import (
    arm_landmarks,
    bottle_wrist_distance_norm,
    check_bottle_wrist,
    check_torso_lean,
    finalize_status,
    shoulder_level_norm,
)
from assessment.movement_state import CheckResult, State, TERMINAL_STATES
from config import (
    BOTTLE_WRIST_MAX_NORM,
    HOLD_FRAMES_REQUIRED,
    PATH_MIN_DELTA_Y,
    SHOULDER_LEVEL_MAX_NORM,
    SIDE_LIFT_Y_MAX,
    START_FRAMES_REQUIRED,
    WAIST_Y_MIN,
)
from vision.bottle_detector import BottleBox
from vision.pose_detector import Landmark


@dataclass
class SideBottleLiftAssessor:
    calibration: Calibration
    state: State = State.NOT_READY
    start_frames: int = 0
    hold_frames: int = 0
    start_x: float | None = None
    start_y: float | None = None
    max_side: float = 0.0
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

        side = self._side()
        shoulder, _, wrist = arm
        bottle_dist = bottle_wrist_distance_norm(
            bottle, wrist, self.calibration.shoulder_width, frame_w, frame_h
        )
        bottle_near = bottle_dist is not None and bottle_dist <= BOTTLE_WRIST_MAX_NORM
        low_start = wrist.y >= WAIST_Y_MIN

        # Sideward progress: wrist moving away from torso center toward dominant side
        outward = (
            (wrist.x - shoulder.x)
            if side == "right"
            else (shoulder.x - wrist.x)
        )

        if self.state == State.UNABLE_TO_ASSESS:
            self.state = State.NOT_READY

        if self.state == State.NOT_READY:
            if low_start and bottle_near:
                self.start_frames += 1
            else:
                self.start_frames = 0
            if self.start_frames >= START_FRAMES_REQUIRED:
                self.state = State.START_POSITION
                self.start_x = wrist.x
                self.start_y = wrist.y
                self.min_y = wrist.y
                self.max_side = outward
            return self.state

        if self.state == State.START_POSITION:
            self.max_side = max(self.max_side, outward)
            self.min_y = min(self.min_y or wrist.y, wrist.y)
            if outward > self.calibration.shoulder_width * 0.35:
                self.state = State.MOVEMENT_IN_PROGRESS
            return self.state

        if self.state == State.MOVEMENT_IN_PROGRESS:
            self.max_side = max(self.max_side, outward)
            self.min_y = min(self.min_y or wrist.y, wrist.y)
            if wrist.y <= SIDE_LIFT_Y_MAX and bottle_near and outward > 0:
                self.state = State.END_POSITION
                self.hold_frames = 0
            return self.state

        if self.state in (State.END_POSITION, State.HOLD_CONFIRMATION):
            self.state = State.HOLD_CONFIRMATION
            if wrist.y <= SIDE_LIFT_Y_MAX and bottle_near:
                self.hold_frames += 1
            else:
                self.hold_frames = max(0, self.hold_frames - 1)

            if self.hold_frames >= HOLD_FRAMES_REQUIRED:
                path_ok = (
                    self.start_y is not None
                    and self.min_y is not None
                    and (self.start_y - self.min_y) >= PATH_MIN_DELTA_Y * 0.5
                    and self.max_side >= self.calibration.shoulder_width * 0.3
                )
                level = shoulder_level_norm(landmarks, self.calibration.shoulder_width)
                level_ok = level is not None and level <= SHOULDER_LEVEL_MAX_NORM * 1.5
                self.checks = [
                    CheckResult(
                        "sideward_path",
                        "Sideward / upward path",
                        "passed" if path_ok else "needs_improvement",
                        "Side lift path detected."
                        if path_ok
                        else "Move the bottle outward and upward more clearly.",
                        measured_value=round(self.max_side, 3),
                        expected_range="outward >= 0.3 shoulder widths",
                    ),
                    CheckResult(
                        "final_height",
                        "Target arm height",
                        "passed" if wrist.y <= SIDE_LIFT_Y_MAX else "needs_improvement",
                        "Reached side-lift height."
                        if wrist.y <= SIDE_LIFT_Y_MAX
                        else "Raise the arm higher to the side.",
                        measured_value=round(wrist.y, 3),
                        expected_range=f"y <= {SIDE_LIFT_Y_MAX}",
                    ),
                    CheckResult(
                        "shoulder_hike",
                        "Limited shoulder lift",
                        "not_assessed"
                        if level is None
                        else ("passed" if level_ok else "needs_improvement"),
                        "Shoulders stayed relatively level."
                        if level_ok
                        else "Avoid excessive shoulder hike.",
                        measured_value=None if level is None else round(level, 3),
                        expected_range=f"<= {SHOULDER_LEVEL_MAX_NORM * 1.5}",
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
