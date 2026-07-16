"""Shared thresholds for Phase 3 movement assessments.

Threshold sources:
- Arm Extension initial values from Phase 0 prototype tuning.
- Remaining movements use the same normalized units (shoulder-width ratios /
  degrees / consecutive frames) documented in elixr_plan.md §11–§12.
- Values are prototype defaults — adjust after expert-rated attempts (Phase 4).
"""

CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# YOLO: COCO class 39 = bottle
BOTTLE_CLASS_ID = 39
BOTTLE_CONF = 0.35
YOLO_EVERY_N_FRAMES = 3

POSE_MIN_DETECTION = 0.5
POSE_MIN_TRACKING = 0.5
LANDMARK_VISIBILITY_MIN = 0.5

# Shared timing / framing
CALIBRATION_FRAMES_REQUIRED = 12
START_FRAMES_REQUIRED = 8
HOLD_FRAMES_REQUIRED = 15
LONG_HOLD_FRAMES_REQUIRED = 45  # balanced stance ~1.5s @ 30fps / ~4.5s @ 10fps
CENTER_X_MIN = 0.30
CENTER_X_MAX = 0.70
SHOULDER_LEVEL_MAX_NORM = 0.15
STANCE_WIDTH_MIN = 0.80
STANCE_WIDTH_MAX = 1.40
STABILITY_JITTER_MAX = 0.035
TORSO_LEAN_MAX_NORM = 0.25
BOTTLE_WRIST_MAX_NORM = 0.55

# Elbow ranges (degrees)
BENT_ELBOW_MAX_DEG = 120.0
BENT_ELBOW_MIN_DEG = 60.0
EXTENDED_ELBOW_MIN_DEG = 150.0

# Bottle hold / lift relative heights (normalized image y; smaller = higher)
WAIST_Y_MIN = 0.45
WAIST_Y_MAX = 0.75
CHEST_Y_MAX = 0.55  # wrist above this (smaller y) counts as lifted to chest
SIDE_LIFT_Y_MAX = 0.50
LOWERING_START_Y_MAX = 0.50  # start must be relatively high
PATH_MIN_DELTA_Y = 0.08

# Transfer
TRANSFER_BOTTLE_WRIST_MAX = 0.60
TRANSFER_MIN_VISIBLE_RATIO = 0.5

DOMINANT_HAND = "right"
ASSESSMENT_VERSION = "3.0"

# Phase 5 tracking confidence / low-confidence latch
MIN_TRACKING_CONFIDENCE = 0.45
LOW_CONFIDENCE_FRAMES_REQUIRED = 5
LOW_CONFIDENCE_RECOVERY_FRAMES = 5

# Set ELIXR_USE_MOCK=1 to keep Phase 2 mock stream instead of live CV.
USE_MOCK_DEFAULT = False

# Movements with written rules + unit tests (Phase 3 exit).
ENABLED_MOVEMENTS = frozenset(
    {
        "ready_stance",
        "balanced_stance_hold",
        "bent_arm_preparation",
        "arm_extension",
        "toss_preparation",
        "basic_bottle_hold",
        "front_bottle_lift",
        "side_bottle_lift",
        "controlled_bottle_lowering",
        "hand_to_hand_transfer",
        "camera_test",
        "camera_readiness",
    }
)
