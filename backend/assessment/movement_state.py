"""Shared assessment states and checkpoint result types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class State(str, Enum):
    NOT_READY = "not_ready"
    START_POSITION = "start_position"
    MOVEMENT_IN_PROGRESS = "movement_in_progress"
    END_POSITION = "end_position"
    HOLD_CONFIRMATION = "hold_confirmation"
    COMPLETED = "completed"
    NEEDS_IMPROVEMENT = "needs_improvement"
    UNABLE_TO_ASSESS = "unable_to_assess"
    # Pre-assessment pipeline states exposed to Flutter
    CAMERA_READY = "camera_ready"
    CALIBRATING = "calibrating"


TERMINAL_STATES = frozenset(
    {
        State.COMPLETED,
        State.NEEDS_IMPROVEMENT,
        State.UNABLE_TO_ASSESS,
    }
)


@dataclass
class CheckResult:
    key: str
    label: str
    status: str  # passed | needs_improvement | not_assessed | in_progress
    message: str
    measured_value: float | None = None
    expected_range: str | None = None
