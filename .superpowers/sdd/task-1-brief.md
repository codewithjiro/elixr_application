### Task 1: Tracking confidence + status reason helpers (TDD)

**Files:**
- Create: `backend/assessment/tracking_confidence.py`
- Create: `backend/assessment/status_reasons.py`
- Create: `backend/assessment/low_confidence.py`
- Modify: `backend/config.py`
- Test: `backend/tests/test_phase5_status.py`

**Interfaces:**
- Consumes: none (pure)
- Produces:
  - `compute_tracking_confidence(*, body: bool, bottle: bool, calibrated: bool) -> float`
  - `StatusReason` string constants + `pick_status_reason(candidates: list[str | None]) -> str | None`
  - `merge_checks_while_unable(previous: list[CheckResult], template: list[CheckResult]) -> list[CheckResult]`
  - `class LowConfidenceGate` with `update(confidence: float) -> bool` returning whether latched

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_phase5_status.py`:

```python
from assessment.tracking_confidence import compute_tracking_confidence
from assessment.status_reasons import (
    CAMERA_UNAVAILABLE,
    INTERNAL_ERROR,
    LOW_TRACKING_CONFIDENCE,
    BODY_NOT_VISIBLE,
    pick_status_reason,
    merge_checks_while_unable,
)
from assessment.low_confidence import LowConfidenceGate
from assessment.movement_state import CheckResult
from config import (
    MIN_TRACKING_CONFIDENCE,
    LOW_CONFIDENCE_FRAMES_REQUIRED,
    LOW_CONFIDENCE_RECOVERY_FRAMES,
)


def test_confidence_formula():
    assert compute_tracking_confidence(body=False, bottle=False, calibrated=False) == 0.0
    assert compute_tracking_confidence(body=True, bottle=False, calibrated=False) == 0.5
    assert compute_tracking_confidence(body=True, bottle=True, calibrated=False) == 0.9
    assert compute_tracking_confidence(body=True, bottle=True, calibrated=True) == 1.0


def test_reason_priority_camera_beats_low_confidence():
    assert (
        pick_status_reason([LOW_TRACKING_CONFIDENCE, CAMERA_UNAVAILABLE, BODY_NOT_VISIBLE])
        == CAMERA_UNAVAILABLE
    )


def test_reason_priority_internal_error_above_low_confidence():
    assert (
        pick_status_reason([LOW_TRACKING_CONFIDENCE, INTERNAL_ERROR])
        == INTERNAL_ERROR
    )


def test_low_confidence_debounce_enter_and_recover():
    gate = LowConfidenceGate(
        min_confidence=MIN_TRACKING_CONFIDENCE,
        enter_frames=LOW_CONFIDENCE_FRAMES_REQUIRED,
        recovery_frames=LOW_CONFIDENCE_RECOVERY_FRAMES,
    )
    low = MIN_TRACKING_CONFIDENCE - 0.1
    high = MIN_TRACKING_CONFIDENCE + 0.1
    for _ in range(LOW_CONFIDENCE_FRAMES_REQUIRED - 1):
        assert gate.update(low) is False
    assert gate.update(low) is True
    for _ in range(LOW_CONFIDENCE_RECOVERY_FRAMES - 1):
        assert gate.update(high) is True
    assert gate.update(high) is False


def test_merge_preserves_passed_blocks_new_passes():
    previous = [
        CheckResult("a", "A", "passed", "ok"),
        CheckResult("b", "B", "in_progress", "working"),
    ]
    template = [
        CheckResult("a", "A", "passed", "ok"),
        CheckResult("b", "B", "passed", "should not promote"),
        CheckResult("c", "C", "passed", "new pass blocked"),
    ]
    merged = merge_checks_while_unable(previous, template)
    by_key = {c.key: c for c in merged}
    assert by_key["a"].status == "passed"
    assert by_key["b"].status != "passed"
    assert by_key["c"].status != "passed"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
python -m pytest tests/test_phase5_status.py -v
```

Expected: FAIL (import / config names missing).

- [ ] **Step 3: Implement helpers + config**

Add to `backend/config.py`:

```python
MIN_TRACKING_CONFIDENCE = 0.45
LOW_CONFIDENCE_FRAMES_REQUIRED = 5
LOW_CONFIDENCE_RECOVERY_FRAMES = 5
```

`backend/assessment/tracking_confidence.py`:

```python
def compute_tracking_confidence(*, body: bool, bottle: bool, calibrated: bool) -> float:
    conf = 0.0
    if body:
        conf += 0.5
    if bottle:
        conf += 0.4
    if calibrated:
        conf += 0.1
    return min(1.0, conf)
```

`backend/assessment/status_reasons.py` — constants, ordered `REASON_PRIORITY` list, `pick_status_reason`, and `merge_checks_while_unable` that:

- starts from `previous` passed keys kept as `passed`;
- for other keys from `template` or `previous`, never upgrades to `passed` while unable;
- maps attempted new passes to `not_assessed` with a short message like “Unable to assess — tracking interrupted.”

`backend/assessment/low_confidence.py` — counter machine matching the tests.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/test_phase5_status.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit (if git available)**

```bash
git add backend/config.py backend/assessment/tracking_confidence.py backend/assessment/status_reasons.py backend/assessment/low_confidence.py backend/tests/test_phase5_status.py
git commit -m "feat(phase5): add tracking confidence, reason priority, and low-confidence gate helpers"
```

---
