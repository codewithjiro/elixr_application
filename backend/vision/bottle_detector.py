"""YOLO11n COCO bottle detection."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from ultralytics import YOLO

from config import BOTTLE_CLASS_ID, BOTTLE_CONF


@dataclass
class BottleBox:
    xmin: float
    ymin: float
    xmax: float
    ymax: float
    confidence: float

    @property
    def center(self) -> tuple[float, float]:
        return ((self.xmin + self.xmax) / 2.0, (self.ymin + self.ymax) / 2.0)

    @property
    def width(self) -> float:
        return self.xmax - self.xmin

    @property
    def height(self) -> float:
        return self.ymax - self.ymin


class BottleDetector:
    def __init__(self, model_name: str = "yolo11n.pt") -> None:
        self._model = YOLO(model_name)
        self._last: BottleBox | None = None

    def detect(self, frame_bgr: np.ndarray) -> BottleBox | None:
        results = self._model.predict(
            source=frame_bgr,
            conf=BOTTLE_CONF,
            classes=[BOTTLE_CLASS_ID],
            verbose=False,
        )
        best: BottleBox | None = None
        if results and results[0].boxes is not None and len(results[0].boxes) > 0:
            boxes = results[0].boxes
            xyxy = boxes.xyxy.cpu().numpy()
            conf = boxes.conf.cpu().numpy()
            for i in range(len(xyxy)):
                cand = BottleBox(
                    float(xyxy[i][0]),
                    float(xyxy[i][1]),
                    float(xyxy[i][2]),
                    float(xyxy[i][3]),
                    float(conf[i]),
                )
                if best is None or cand.confidence > best.confidence:
                    best = cand
        self._last = best
        return best

    @property
    def last(self) -> BottleBox | None:
        return self._last
