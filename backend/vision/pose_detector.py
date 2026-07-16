"""MediaPipe Tasks Pose landmarker in LIVE_STREAM mode (non-blocking)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading
import time
import urllib.request

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core import base_options as base_options_module
from mediapipe.tasks.python.vision.core import vision_task_running_mode as running_mode_module

from config import LANDMARK_VISIBILITY_MIN, POSE_MIN_DETECTION

# Classical BlazePose index -> name (subset used by ELIXR rules)
LANDMARK_NAMES = {
    11: "left_shoulder",
    12: "right_shoulder",
    13: "left_elbow",
    14: "right_elbow",
    15: "left_wrist",
    16: "right_wrist",
    23: "left_hip",
    24: "right_hip",
    27: "left_ankle",
    28: "right_ankle",
}

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
)
MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "pose_landmarker_lite.task"

# Cap pose submissions so inference does not starve the main loop.
_POSE_MIN_INTERVAL_S = 1.0 / 15.0


@dataclass
class Landmark:
    x: float
    y: float
    z: float
    visibility: float

    @property
    def visible(self) -> bool:
        return self.visibility >= LANDMARK_VISIBILITY_MIN


def _ensure_model() -> Path:
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not MODEL_PATH.exists():
        print(f"Downloading pose model to {MODEL_PATH} …")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    return MODEL_PATH


def _visibility_of(landmark) -> float:
    """Read visibility without treating 0.0 as missing (``x or 1.0`` bug)."""
    raw = getattr(landmark, "visibility", None)
    if raw is None:
        return 1.0
    return float(raw)


def _landmarks_from_result(result) -> dict[str, Landmark] | None:
    if not result.pose_landmarks:
        return None
    pose = result.pose_landmarks[0]
    out: dict[str, Landmark] = {}
    for idx, name in LANDMARK_NAMES.items():
        if idx >= len(pose):
            continue
        p = pose[idx]
        out[name] = Landmark(float(p.x), float(p.y), float(p.z), _visibility_of(p))
    return out


class PoseDetector:
    def __init__(self) -> None:
        model = _ensure_model()
        options = vision.PoseLandmarkerOptions(
            base_options=base_options_module.BaseOptions(model_asset_path=str(model)),
            running_mode=running_mode_module.VisionTaskRunningMode.LIVE_STREAM,
            num_poses=1,
            min_pose_detection_confidence=POSE_MIN_DETECTION,
            min_tracking_confidence=0.5,
            result_callback=self._on_result,
        )
        self._landmarker = vision.PoseLandmarker.create_from_options(options)
        self._lock = threading.Lock()
        self._latest: dict[str, Landmark] | None = None
        self._last_submit_s = 0.0
        self._last_timestamp_ms = -1

    def _on_result(self, result, _image, _timestamp_ms: int) -> None:
        landmarks = _landmarks_from_result(result)
        with self._lock:
            self._latest = landmarks

    def process(self, frame_bgr: np.ndarray) -> dict[str, Landmark] | None:
        """Submit frame asynchronously (~15 FPS) and return the latest pose."""
        now_s = time.monotonic()
        if now_s - self._last_submit_s >= _POSE_MIN_INTERVAL_S:
            timestamp_ms = int(now_s * 1000)
            if timestamp_ms > self._last_timestamp_ms:
                rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                self._landmarker.detect_async(mp_image, timestamp_ms)
                self._last_submit_s = now_s
                self._last_timestamp_ms = timestamp_ms

        with self._lock:
            return self._latest

    def draw(self, frame_bgr: np.ndarray, landmarks: dict[str, Landmark] | None) -> None:
        if landmarks is None:
            return
        h, w = frame_bgr.shape[:2]
        for lm in landmarks.values():
            if lm.visible:
                cv2.circle(
                    frame_bgr,
                    (int(lm.x * w), int(lm.y * h)),
                    4,
                    (0, 255, 180),
                    -1,
                )

    def close(self) -> None:
        self._landmarker.close()
