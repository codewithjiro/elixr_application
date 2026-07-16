"""Debounced low-confidence latch for unable-to-assess overlay."""


class LowConfidenceGate:
    def __init__(
        self,
        *,
        min_confidence: float,
        enter_frames: int,
        recovery_frames: int,
    ) -> None:
        self._min_confidence = min_confidence
        self._enter_frames = enter_frames
        self._recovery_frames = recovery_frames
        self._latched = False
        self._low_count = 0
        self._high_count = 0

    def update(self, confidence: float) -> bool:
        if confidence < self._min_confidence:
            self._low_count += 1
            self._high_count = 0
            if not self._latched and self._low_count >= self._enter_frames:
                self._latched = True
        else:
            self._high_count += 1
            self._low_count = 0
            if self._latched and self._high_count >= self._recovery_frames:
                self._latched = False

        return self._latched
