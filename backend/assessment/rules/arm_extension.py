"""Arm Extension multi-frame state machine."""

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
    BENT_ELBOW_MAX_DEG,
    BOTTLE_WRIST_MAX_NORM,
    EXTENDED_ELBOW_MIN_DEG,
    HOLD_FRAMES_REQUIRED,
    START_FRAMES_REQUIRED,
    TORSO_LEAN_MAX_NORM,
)
from vision import geometry
from vision.bottle_detector import BottleBox
from vision.pose_detector import Landmark


@dataclass
class ArmExtensionAssessor:
    calibration: Calibration
    state: State = State.NOT_READY
    start_frames: int = 0
    hold_frames: int = 0
    checks: list[CheckResult] = field(default_factory=list)
    last_elbow: float | None = None
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
                    "Required pose landmarks not visible.",
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

        shoulder, elbow, wrist = arm
        elbow_angle = geometry.angle_deg(shoulder, elbow, wrist)
        self.last_elbow = elbow_angle
        lean = geometry.torso_lean_norm(landmarks, self.calibration.shoulder_width)
        bottle_dist = bottle_wrist_distance_norm(
            bottle, wrist, self.calibration.shoulder_width, frame_w, frame_h
        )
        bottle_near = bottle_dist is not None and bottle_dist <= BOTTLE_WRIST_MAX_NORM

        if self.state == State.UNABLE_TO_ASSESS:
            self.state = State.NOT_READY

        if self.state == State.NOT_READY:
            if elbow_angle <= BENT_ELBOW_MAX_DEG and bottle_near:
                self.start_frames += 1
            else:
                self.start_frames = 0
            if self.start_frames >= START_FRAMES_REQUIRED:
                self.state = State.START_POSITION
            return self.state

        if self.state == State.START_POSITION:
            if elbow_angle > BENT_ELBOW_MAX_DEG + 10:
                self.state = State.MOVEMENT_IN_PROGRESS
            return self.state

        if self.state == State.MOVEMENT_IN_PROGRESS:
            if elbow_angle >= EXTENDED_ELBOW_MIN_DEG:
                self.state = State.END_POSITION
                self.hold_frames = 0
            return self.state

        if self.state in (State.END_POSITION, State.HOLD_CONFIRMATION):
            self.state = State.HOLD_CONFIRMATION
            if (
                elbow_angle >= EXTENDED_ELBOW_MIN_DEG
                and bottle_near
                and (lean is None or lean <= TORSO_LEAN_MAX_NORM)
            ):
                self.hold_frames += 1
            else:
                self.hold_frames = max(0, self.hold_frames - 1)

            if self.hold_frames >= HOLD_FRAMES_REQUIRED:
                self.checks = self._final_checks(
                    elbow_angle, bottle, wrist, landmarks, frame_w, frame_h
                )
                self.state = finalize_status(self.checks)
            return self.state

        return self.state

    def _final_checks(
        self,
        elbow_angle: float,
        bottle: BottleBox | None,
        wrist: Landmark,
        landmarks: dict[str, Landmark],
        frame_w: int,
        frame_h: int,
    ) -> list[CheckResult]:
        checks: list[CheckResult] = [
            CheckResult(
                "start_bent_elbow",
                "Valid bent-elbow start",
                "passed",
                "Start position was detected.",
            ),
            check_bottle_wrist(
                bottle,
                wrist,
                self.calibration.shoulder_width,
                frame_w,
                frame_h,
            ),
            CheckResult(
                "elbow_extension",
                "Elbow extended",
                "passed"
                if elbow_angle >= EXTENDED_ELBOW_MIN_DEG
                else "needs_improvement",
                "Elbow extension within range."
                if elbow_angle >= EXTENDED_ELBOW_MIN_DEG
                else "Straighten your elbow toward full extension.",
                measured_value=round(elbow_angle, 1),
                expected_range=f">= {EXTENDED_ELBOW_MIN_DEG} degrees",
            ),
            check_torso_lean(landmarks, self.calibration.shoulder_width),
            CheckResult(
                "hold_duration",
                "Final pose hold",
                "passed",
                f"Held for {HOLD_FRAMES_REQUIRED} consecutive frames.",
                measured_value=float(HOLD_FRAMES_REQUIRED),
                expected_range=f">= {HOLD_FRAMES_REQUIRED} frames",
            ),
        ]
        return checks
