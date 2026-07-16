"""FPS and latency measurement helpers."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class Metrics:
    frame_times: deque[float] = field(default_factory=lambda: deque(maxlen=120))
    latencies_ms: deque[float] = field(default_factory=lambda: deque(maxlen=120))
    bottle_true: int = 0
    bottle_false: int = 0
    bottle_miss: int = 0
    _last_t: float | None = None

    def mark_frame_start(self) -> float:
        return time.perf_counter()

    def mark_frame_end(self, start: float) -> None:
        now = time.perf_counter()
        self.latencies_ms.append((now - start) * 1000.0)
        if self._last_t is not None:
            dt = now - self._last_t
            if dt > 0:
                self.frame_times.append(1.0 / dt)
        self._last_t = now

    @property
    def fps(self) -> float:
        if not self.frame_times:
            return 0.0
        return sum(self.frame_times) / len(self.frame_times)

    @property
    def median_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        vals = sorted(self.latencies_ms)
        mid = len(vals) // 2
        if len(vals) % 2:
            return vals[mid]
        return (vals[mid - 1] + vals[mid]) / 2.0

    @property
    def min_fps(self) -> float:
        if not self.frame_times:
            return 0.0
        return min(self.frame_times)

    @property
    def p95_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        vals = sorted(self.latencies_ms)
        idx = int(round(0.95 * (len(vals) - 1)))
        return vals[idx]

    def report(self) -> dict[str, float | int]:
        return {
            "avg_fps": round(self.fps, 2),
            "min_fps": round(self.min_fps, 2),
            "median_latency_ms": round(self.median_latency_ms, 1),
            "p95_latency_ms": round(self.p95_latency_ms, 1),
            "bottle_true": self.bottle_true,
            "bottle_false": self.bottle_false,
            "bottle_miss": self.bottle_miss,
            "samples": len(self.latencies_ms),
        }

    def summary(self) -> str:
        return (
            f"FPS~{self.fps:.1f}  "
            f"latency_med={self.median_latency_ms:.0f}ms  "
            f"bottle hits={self.bottle_true} misses={self.bottle_miss}"
        )
