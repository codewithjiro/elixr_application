# Task 1 Report: Tracking confidence + status reason helpers (TDD)

**Date:** 2026-07-15  
**Status:** DONE  
**Phase:** 5 — Polish, documentation, design  
**Scope:** Pure Python helpers + config constants only (no `live_session` wiring)

---

## Summary

Implemented four new assessment helpers and three config constants per the task brief, following strict TDD (RED → GREEN). All five specified tests pass. Existing unittest suite (18 tests) remains green.

---

## Files Created / Modified

| Action | File |
|--------|------|
| Create | `backend/assessment/tracking_confidence.py` |
| Create | `backend/assessment/status_reasons.py` |
| Create | `backend/assessment/low_confidence.py` |
| Modify | `backend/config.py` (3 constants appended) |
| Create | `backend/tests/test_phase5_status.py` |

---

## TDD Evidence

### Step 1 — Write failing tests

Created `backend/tests/test_phase5_status.py` verbatim from the task brief (5 test functions).

### Step 2 — RED (verify failure)

```bash
cd backend
python -m pytest tests/test_phase5_status.py -v
```

**Result:** ERROR during collection (expected).

```
ModuleNotFoundError: No module named 'assessment.tracking_confidence'
```

Failure reason: missing implementation modules and config constants — correct RED signal (not a typo or wrong assertion).

> Note: `pytest` was not pre-installed; installed via `pip install pytest` before running. This is an environment setup step, not a code change.

### Step 3 — Implement helpers + config

**`backend/config.py`** — added:

```python
MIN_TRACKING_CONFIDENCE = 0.45
LOW_CONFIDENCE_FRAMES_REQUIRED = 5
LOW_CONFIDENCE_RECOVERY_FRAMES = 5
```

**`backend/assessment/tracking_confidence.py`** — `compute_tracking_confidence(*, body, bottle, calibrated) -> float` per brief formula (0.5 body + 0.4 bottle + 0.1 calibrated, capped at 1.0).

**`backend/assessment/status_reasons.py`** — fixed string constants, `REASON_PRIORITY` list (spec §4.3 order), `pick_status_reason`, and `merge_checks_while_unable`:

- Preserves `passed` keys from `previous`.
- Blocks new `passed` promotions while unable → `not_assessed` with message `"Unable to assess — tracking interrupted."`
- Non-passed statuses (e.g. `in_progress`) retained unchanged.

**`backend/assessment/low_confidence.py`** — `LowConfidenceGate` counter machine:

- `update(confidence)` returns current latched state (`bool`).
- Enter: `enter_frames` consecutive frames below `min_confidence` → latch ON.
- Recovery: `recovery_frames` consecutive frames at/above threshold → latch OFF.

### Step 4 — GREEN (verify pass)

```bash
cd backend
python -m pytest tests/test_phase5_status.py -v
```

**Result:** 5 passed in 0.03s

```
tests/test_phase5_status.py::test_confidence_formula PASSED
tests/test_phase5_status.py::test_reason_priority_camera_beats_low_confidence PASSED
tests/test_phase5_status.py::test_reason_priority_internal_error_above_low_confidence PASSED
tests/test_phase5_status.py::test_low_confidence_debounce_enter_and_recover PASSED
tests/test_phase5_status.py::test_merge_preserves_passed_blocks_new_passes PASSED
```

### Regression check

```bash
cd backend
python -m unittest discover -s tests -v
```

**Result:** 18 tests OK (existing suite unaffected).

---

## Self-Review

### Correctness

| Helper | Behavior | Test coverage |
|--------|----------|---------------|
| `compute_tracking_confidence` | Formula matches brief exactly | `test_confidence_formula` |
| `pick_status_reason` | Highest-priority reason from candidates; `None` filtered | 2 priority tests |
| `LowConfidenceGate` | Debounce enter (5 frames) + recovery (5 frames) | `test_low_confidence_debounce_enter_and_recover` |
| `merge_checks_while_unable` | Preserve prior passes; block new passes | `test_merge_preserves_passed_blocks_new_passes` |

### Design alignment with spec (§4.2–§4.5)

- `REASON_PRIORITY` includes all seven backend-emit reasons in documented order.
- Constants use snake_case string values (`camera_unavailable`, etc.) matching the FrameEvent enum spec.
- `merge_checks_while_unable` implements §4.5 checkpoint freeze rules at the helper level.

### Intentional non-changes

- Did **not** wire into `live_session.py` (Task 2 scope).
- Did **not** add `pytest` to `requirements.txt` (not requested; brief only uses pytest for this test file).
- Did **not** commit (no git repository per instructions).

### Minor observations (non-blocking)

1. `test_phase5_status.py` omits the `sys.path.insert` pattern used by older unittest files; pytest from `backend/` cwd resolves imports correctly.
2. `pytest` was installed ad-hoc in this environment; CI/other devs may need it available.

---

## Interfaces Delivered

```python
compute_tracking_confidence(*, body: bool, bottle: bool, calibrated: bool) -> float

# status_reasons.py
CAMERA_UNAVAILABLE, CAMERA_READ_FAILED, MODELS_UNAVAILABLE,
INTERNAL_ERROR, LOW_TRACKING_CONFIDENCE, BODY_NOT_VISIBLE, BOTTLE_NOT_VISIBLE
REASON_PRIORITY: list[str]
pick_status_reason(candidates: list[str | None]) -> str | None
merge_checks_while_unable(previous: list[CheckResult], template: list[CheckResult]) -> list[CheckResult]

class LowConfidenceGate:
    def __init__(self, *, min_confidence: float, enter_frames: int, recovery_frames: int) -> None
    def update(self, confidence: float) -> bool

# config.py
MIN_TRACKING_CONFIDENCE = 0.45
LOW_CONFIDENCE_FRAMES_REQUIRED = 5
LOW_CONFIDENCE_RECOVERY_FRAMES = 5
```

---

## Commits

None (no git repository).

---

## Ready for Task 2

Helpers are pure, tested, and config constants are in place. Task 2 can import and wire into `live_session.py` / `FrameEvent` schema.
