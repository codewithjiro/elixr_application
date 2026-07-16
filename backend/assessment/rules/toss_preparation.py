"""Toss Preparation Position — stance + bent elbow + bottle hold."""

from __future__ import annotations

from dataclasses import dataclass, field

from assessment.calibration import Calibration
from assessment.checks import (
    REQUIRED_FULL_BODY,
    arm_landmarks,
    bottle_wrist_distance_norm,
    check_body_visibility,
    check_bottle_wrist,
    check_stance_width,
    finalize_status,
    required_visible,
)
from assessment.movement_state import CheckResult, State, TERMINAL_STATES
from config import (
    BENT_ELBOW_MAX_DEG,
    BENT_ELBOW_MIN_DEG,
    BOTTLE_WRIST_MAX_NORM,
    HOLD_FRAMES_REQUIRED,
    START_FRAMES_REQUIRED,
)
from vision import geometry
from vision.bottle_detector import BottleBox
from vision.pose_detector import Landmark


@dataclass
class TossPreparationAssessor:
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

        if landmarks is None or not required_visible(landmarks, REQUIRED_FULL_BODY):
            self.state = State.UNABLE_TO_ASSESS
            self.checks = [
                CheckResult(
                    "body_visibility",
                    "Body visibility",
                    "not_assessed",
                    "Full body not visible for toss preparation.",
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
        bent = BENT_ELBOW_MIN_DEG <= elbow_angle <= BENT_ELBOW_MAX_DEG
        bottle_dist = bottle_wrist_distance_norm(
            bottle, wrist, self.calibration.shoulder_width, frame_w, frame_h
        )
        bottle_near = bottle_dist is not None and bottle_dist <= BOTTLE_WRIST_MAX_NORM
        pose_ok = bent and bottle_near

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
                    check_body_visibility(landmarks),
                    check_stance_width(landmarks, self.calibration.shoulder_width),
                    CheckResult(
                        "elbow_angle",
                        "Bent elbow prep",
                        "passed" if bent else "needs_improvement",
                        "Elbow ready for toss prep."
                        if bent
                        else "Bend the elbow into the prep range.",
                        measured_value=round(elbow_angle, 1),
                        expected_range=f"{BENT_ELBOW_MIN_DEG}-{BENT_ELBOW_MAX_DEG} degrees",
                    ),
                    check_bottle_wrist(
                        bottle,
                        wrist,
                        self.calibration.shoulder_width,
                        frame_w,
                        frame_h,
                    ),
                    CheckResult(
                        "hold_duration",
                        "Stable prep hold",
                        "passed",
                        f"Held for {HOLD_FRAMES_REQUIRED} frames.",
                        measured_value=float(HOLD_FRAMES_REQUIRED),
                        expected_range=f">= {HOLD_FRAMES_REQUIRED} frames",
                    ),
                ]
                self.state = finalize_status(self.checks)
            return self.state

        return self.state
