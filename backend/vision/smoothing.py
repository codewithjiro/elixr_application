"""Short rolling-window smoothing for landmarks and bottle center."""

from __future__ import annotations

from collections import deque

from vision.bottle_detector import BottleBox
from vision.pose_detector import Landmark


class Smoother:
    def __init__(self, window: int = 5) -> None:
        self._window = window
        self._lm: dict[str, deque[Landmark]] = {}
        self._bottle: deque[BottleBox] = deque(maxlen=window)

    def push_landmarks(self, landmarks: dict[str, Landmark] | None) -> dict[str, Landmark] | None:
        if landmarks is None:
            return None
        out: dict[str, Landmark] = {}
        for name, lm in landmarks.items():
            if name not in self._lm:
                self._lm[name] = deque(maxlen=self._window)
            self._lm[name].append(lm)
            xs = [p.x for p in self._lm[name]]
            ys = [p.y for p in self._lm[name]]
            zs = [p.z for p in self._lm[name]]
            vs = [p.visibility for p in self._lm[name]]
            out[name] = Landmark(
                sum(xs) / len(xs),
                sum(ys) / len(ys),
                sum(zs) / len(zs),
                sum(vs) / len(vs),
            )
        return out

    def push_bottle(self, box: BottleBox | None) -> BottleBox | None:
        if box is None:
            self._bottle.clear()
            return None
        self._bottle.append(box)
        n = len(self._bottle)
        return BottleBox(
            sum(b.xmin for b in self._bottle) / n,
            sum(b.ymin for b in self._bottle) / n,
            sum(b.xmax for b in self._bottle) / n,
            sum(b.ymax for b in self._bottle) / n,
            sum(b.confidence for b in self._bottle) / n,
        )
