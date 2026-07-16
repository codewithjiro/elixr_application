"""Measure assessment FPS and latency on the reference camera/hardware.

Runs MediaPipe Pose + YOLO (every N frames) for a fixed duration.
Does not open a GUI window.

Run from backend/:
  python -m eval.benchmark_performance --seconds 30 --out eval/reports/perf.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import YOLO_EVERY_N_FRAMES
from metrics import Metrics
from vision.bottle_detector import BottleDetector
from vision.camera import Camera
from vision.pose_detector import PoseDetector
from vision.smoothing import Smoother


def run_benchmark(camera_index: int, seconds: float) -> dict:
    camera = Camera(camera_index)
    camera.open()
    pose = PoseDetector()
    bottle = BottleDetector()
    smoother = Smoother(window=5)
    metrics = Metrics()

    frame_i = 0
    t_end = time.perf_counter() + seconds
    try:
        while time.perf_counter() < t_end:
            t0 = metrics.mark_frame_start()
            ok, frame = camera.read()
            if not ok or frame is None:
                break

            landmarks = pose.detect(frame)
            landmarks = smoother.push_landmarks(landmarks)

            if frame_i % YOLO_EVERY_N_FRAMES == 0:
                box = bottle.detect(frame)
                box = smoother.push_bottle(box)
                if box is not None:
                    metrics.bottle_true += 1
                else:
                    metrics.bottle_miss += 1

            metrics.mark_frame_end(t0)
            frame_i += 1
    finally:
        camera.release()

    report = metrics.report()
    report["duration_seconds"] = seconds
    report["frames"] = frame_i
    report["yolo_every_n"] = YOLO_EVERY_N_FRAMES
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="FPS / latency benchmark")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    report = run_benchmark(args.camera, args.seconds)
    print(json.dumps(report, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
