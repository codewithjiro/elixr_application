"""Basic Hand-to-Hand Transfer — bottle moves from one wrist zone to the other.

Highest-risk movement. Uses approximate proximity only — not grip or catch quality.
Known failure: occlusion, blur, and depth ambiguity can produce Unable to Assess.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from assessment.calibration import Calibration
from assessment.checks import bottle_wrist_distance_norm, finalize_status
from assessment.movement_state import CheckResult, State, TERMINAL_STATES
from config import (
    HOLD_FRAMES_REQUIRED,
    START_FRAMES_REQUIRED,
    TRANSFER_BOTTLE_WRIST_MAX,
    TRANSFER_MIN_VISIBLE_RATIO,
)
from vision.bottle_detector import BottleBox
from vision.pose_detector import Landmark


@dataclass
class HandToHandTransferAssessor:
    calibration: Calibration
    state: State = State.NOT_READY
    start_frames: int = 0
    hold_frames: int = 0
    frames_seen: int = 0
    frames_bottle: int = 0
    started_near_first: bool = False
    checks: list[CheckResult] = field(default_factory=list)
    requires_bottle: bool = True

    def _first_side(self) -> str:
        return "right" if self.calibration.dominant_hand == "right" else "left"

    def _second_side(self) -> str:
        return "left" if self._first_side() == "right" else "right"

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

        w1 = landmarks.get(f"{self._first_side()}_wrist")
        w2 = landmarks.get(f"{self._second_side()}_wrist")
        if w1 is None or w2 is None or not w1.visible or not w2.visible:
            self.state = State.UNABLE_TO_ASSESS
            self.checks = [
                CheckResult(
                    "both_wrists",
                    "Both wrists visible",
                    "not_assessed",
                    "Both wrists must be visible for transfer assessment.",
                )
            ]
            return self.state

        self.frames_seen += 1
        if bottle is not None:
            self.frames_bottle += 1

        d1 = bottle_wrist_distance_norm(
            bottle, w1, self.calibration.shoulder_width, frame_w, frame_h
        )
        d2 = bottle_wrist_distance_norm(
            bottle, w2, self.calibration.shoulder_width, frame_w, frame_h
        )
        near1 = d1 is not None and d1 <= TRANSFER_BOTTLE_WRIST_MAX
        near2 = d2 is not None and d2 <= TRANSFER_BOTTLE_WRIST_MAX

        if self.state == State.UNABLE_TO_ASSESS:
            self.state = State.NOT_READY

        if self.state == State.NOT_READY:
            if near1 and not near2:
                self.start_frames += 1
            else:
                self.start_frames = 0
            if self.start_frames >= START_FRAMES_REQUIRED:
                self.state = State.START_POSITION
                self.started_near_first = True
            return self.state

        if self.state == State.START_POSITION:
            if bottle is not None and not near1:
                self.state = State.MOVEMENT_IN_PROGRESS
            return self.state

        if self.state == State.MOVEMENT_IN_PROGRESS:
            if near2:
                self.state = State.END_POSITION
                self.hold_frames = 0
            return self.state

        if self.state in (State.END_POSITION, State.HOLD_CONFIRMATION):
            self.state = State.HOLD_CONFIRMATION
            if near2:
                self.hold_frames += 1
            else:
                self.hold_frames = max(0, self.hold_frames - 1)

            if self.hold_frames >= HOLD_FRAMES_REQUIRED:
                visible_ratio = (
                    self.frames_bottle / self.frames_seen if self.frames_seen else 0.0
                )
                visible_ok = visible_ratio >= TRANSFER_MIN_VISIBLE_RATIO
                self.checks = [
                    CheckResult(
                        "start_near_first",
                        "Bottle starts near first wrist",
                        "passed" if self.started_near_first else "needs_improvement",
                        "Started near the first wrist."
                        if self.started_near_first
                        else "Begin with the bottle near the first hand.",
                    ),
                    CheckResult(
                        "both_wrists",
                        "Both wrists visible",
                        "passed",
                        "Both wrists stayed visible.",
                    ),
                    CheckResult(
                        "end_near_second",
                        "Bottle ends near second wrist",
                        "passed" if near2 else "needs_improvement",
                        "Bottle finished near the second wrist."
                        if near2
                        else "Finish with the bottle near the other wrist.",
                        measured_value=None if d2 is None else round(d2, 3),
                        expected_range=f"<= {TRANSFER_BOTTLE_WRIST_MAX}",
                    ),
                    CheckResult(
                        "bottle_visibility_ratio",
                        "Bottle remains detectable",
                        "passed" if visible_ok else "not_assessed",
                        "Bottle was visible enough to assess."
                        if visible_ok
                        else "Bottle disappeared too often — Unable to Assess.",
                        measured_value=round(visible_ratio, 3),
                        expected_range=f">= {TRANSFER_MIN_VISIBLE_RATIO}",
                    ),
                ]
                self.state = finalize_status(self.checks)
            return self.state

        return self.state
