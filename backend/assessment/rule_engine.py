"""Movement assessor registry / factory."""

from __future__ import annotations

from typing import Any, Callable

from assessment.calibration import Calibration
from assessment.movement_state import State
from assessment.rules.arm_extension import ArmExtensionAssessor
from assessment.rules.balanced_stance_hold import BalancedStanceHoldAssessor
from assessment.rules.basic_bottle_hold import BasicBottleHoldAssessor
from assessment.rules.bent_arm_preparation import BentArmPreparationAssessor
from assessment.rules.controlled_bottle_lowering import ControlledBottleLoweringAssessor
from assessment.rules.front_bottle_lift import FrontBottleLiftAssessor
from assessment.rules.hand_to_hand_transfer import HandToHandTransferAssessor
from assessment.rules.ready_stance import ReadyStanceAssessor
from assessment.rules.side_bottle_lift import SideBottleLiftAssessor
from assessment.rules.toss_preparation import TossPreparationAssessor
from config import ENABLED_MOVEMENTS

AssessorFactory = Callable[[Calibration], Any]

_REGISTRY: dict[str, AssessorFactory] = {
    "ready_stance": ReadyStanceAssessor,
    "balanced_stance_hold": BalancedStanceHoldAssessor,
    "basic_bottle_hold": BasicBottleHoldAssessor,
    "front_bottle_lift": FrontBottleLiftAssessor,
    "side_bottle_lift": SideBottleLiftAssessor,
    "bent_arm_preparation": BentArmPreparationAssessor,
    "arm_extension": ArmExtensionAssessor,
    "controlled_bottle_lowering": ControlledBottleLoweringAssessor,
    "hand_to_hand_transfer": HandToHandTransferAssessor,
    "toss_preparation": TossPreparationAssessor,
}

# Movements that require a bottle detection for readiness
BOTTLE_REQUIRED = frozenset(
    {
        "basic_bottle_hold",
        "front_bottle_lift",
        "side_bottle_lift",
        "bent_arm_preparation",
        "arm_extension",
        "controlled_bottle_lowering",
        "hand_to_hand_transfer",
        "toss_preparation",
    }
)


def is_enabled(movement_id: str) -> bool:
    return movement_id in ENABLED_MOVEMENTS


def requires_bottle(movement_id: str) -> bool:
    return movement_id in BOTTLE_REQUIRED


def create_assessor(movement_id: str, calibration: Calibration) -> Any:
    factory = _REGISTRY.get(movement_id)
    if factory is None:
        raise ValueError(f"No assessor registered for movement_id={movement_id}")
    return factory(calibration)


def step_label(state: State) -> str:
    return {
        State.NOT_READY: "get_ready",
        State.START_POSITION: "hold_start",
        State.MOVEMENT_IN_PROGRESS: "perform_movement",
        State.END_POSITION: "reach_end",
        State.HOLD_CONFIRMATION: "hold_final",
        State.COMPLETED: "complete",
        State.NEEDS_IMPROVEMENT: "review_feedback",
        State.UNABLE_TO_ASSESS: "unable_to_assess",
        State.CAMERA_READY: "readiness_check",
        State.CALIBRATING: "calibration",
    }.get(state, state.value)
