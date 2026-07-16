# Phase 5 Polish and Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Phase 5 polish — consistent status reasons, low-confidence debounce with frozen checkpoints, soft safety before practice, clearer errors/UI, and reproducible README/claims docs — without redesigning or breaking Phase 0–4 flows.

**Architecture:** Extract pure helpers for `tracking_confidence`, reason priority, and low-confidence latch; wire them into `LiveAssessmentSession` so assessor `update()` is skipped while unable while previously `passed` checkpoints are preserved. Flutter parses additive optional fields, shows banners/chips with restrained animation, and soft-gates practice Start with a session-only safety sheet. Docs replace the root README and add `README_PHASE5.md`.

**Tech Stack:** Flutter (Windows desktop), Dart, FastAPI/WebSocket, Pydantic, pytest, existing MediaPipe/YOLO pipeline.

## Global Constraints

- Additive WebSocket fields only; missing `status_reason` / `status_message` must not break Flutter.
- `assessment_state` is source of truth; `status_reason` explains why.
- No new package dependencies without asking.
- No router rewrite for page transitions.
- Prefer checkpoint/session metrics language; no skill “score” freeze wording.
- Soft safety: dismiss and “continue” both allow practice; “don’t show again” is in-memory only.
- Do not claim offline mock as primary assessment mode in README/onboarding/manuscript Implemented tier.
- Resume assessor after recovery without full sequence reset; full reset only on new session.
- >3 files OK if Phase-5-focused.
- Repo may have no git root: skip commit steps when `git rev-parse` fails; do not invent a repo.
- Spec: `docs/superpowers/specs/2026-07-15-phase5-polish-documentation-design.md`

---

## File map

| File | Responsibility |
|---|---|
| `backend/config.py` | `MIN_TRACKING_CONFIDENCE`, enter/recovery frame counts |
| `backend/assessment/tracking_confidence.py` | Pure composite confidence formula |
| `backend/assessment/status_reasons.py` | Enum constants + priority picker + check merge helpers |
| `backend/assessment/low_confidence.py` | Enter/exit latch counters |
| `backend/schemas/frame_event.py` | Optional `status_reason`, `status_message` |
| `backend/assessment/live_session.py` | Wire helpers; freeze assessor; map camera/model/errors |
| `backend/vision/camera.py` / `api/websocket.py` | Clearer errors / optional reason on error payloads when cheap |
| `backend/tests/test_phase5_status.py` | Formula, priority, debounce, preserve, freeze |
| `lib/services/websocket_service.dart` | Optional fields; client reason codes |
| `lib/core/constants/status_reasons.dart` | Shared string constants + banner copy helper |
| `lib/core/widgets/status_chip.dart` | AnimatedSwitcher cross-fade |
| `lib/features/practice/practice_safety.dart` | Session-only soft safety sheet API |
| `lib/features/practice/practice_shell_screen.dart` | Safety before Start; banners; Semantics |
| `lib/features/camera_test/camera_test_screen.dart` | Live copy + banners |
| `lib/features/onboarding/onboarding_screen.dart` | Live-assessment narrative |
| `lib/features/safety/safety_screen.dart` | §20-aligned guidelines |
| `test/frame_event_parse_test.dart` | Missing/present optional fields |
| `test/status_banner_test.dart` | Banner helper / chip smoke |
| `README.md` | Setup + troubleshooting |
| `backend/README_PHASE5.md` | Phase 5 notes + claims + demo checklist |
| `backend/assessment/LIMITATIONS.md` | Light sync if needed |
| `elixr_plan.md` | Mark Phase 5 todo completed at end |

---

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

### Task 2: FrameEvent schema + live session wiring

**Files:**
- Modify: `backend/schemas/frame_event.py`
- Modify: `backend/assessment/live_session.py`
- Modify: `backend/vision/camera.py` (clearer raise/messages if needed)
- Modify: `backend/api/websocket.py` (optional `status_reason` on `type:error`)
- Test: extend `backend/tests/test_phase5_status.py` with schema accept + a lightweight session-double test if assessor freeze is harder — prefer testing a small `_apply_unable_overlay` method extracted on the session module

**Interfaces:**
- Consumes: Task 1 helpers
- Produces: `FrameEvent` with optional `status_reason: str | None = None`, `status_message: str | None = None`; live session emits them; while latched, does not call `_assessor.update`

- [ ] **Step 1: Write failing tests for schema + freeze helper**

Append:

```python
from schemas.frame_event import FrameEvent


def test_frame_event_optional_fields_omitted():
    ev = FrameEvent(
        movement_id="arm_extension",
        assessment_state="calibrating",
        body_detected=True,
        bottle_detected=False,
        tracking_confidence=0.5,
        current_step="calibration",
        frame_jpeg_base64="",
    )
    data = ev.to_dict()
    assert data.get("status_reason") in (None, )
    # model_dump may include null — accept None
    assert data.get("status_message") in (None, )


def test_frame_event_optional_fields_set():
    ev = FrameEvent(
        movement_id="arm_extension",
        assessment_state="unable_to_assess",
        body_detected=False,
        bottle_detected=False,
        tracking_confidence=0.2,
        current_step="unable_to_assess",
        frame_jpeg_base64="",
        status_reason=LOW_TRACKING_CONFIDENCE,
        status_message="Improve lighting and framing, then hold steady.",
    )
    assert ev.status_reason == LOW_TRACKING_CONFIDENCE
```

Also add a unit test for an extracted helper used by the session, e.g. `should_freeze_assessor(latched: bool, hard_unable: bool) -> bool`.

- [ ] **Step 2: Run tests — expect failure on missing FrameEvent fields**

```bash
cd backend
python -m pytest tests/test_phase5_status.py -v
```

- [ ] **Step 3: Implement schema + session wiring**

In `frame_event.py` add optional fields.

In `live_session.py`:

1. Replace inline confidence with `compute_tracking_confidence`.
2. Own `LowConfidenceGate` on the session.
3. On models unavailable / camera failures / caught internal exceptions: set unable + reason via `pick_status_reason`.
4. When gate latched or hard unable: **skip** `_assessor.update(...)`; build checks via `merge_checks_while_unable(self._last_good_passed_checks, ...)`; set `assessment_state` to `unable_to_assess` (unless camera_test special-cases readiness — still show reasons).
5. When not frozen: call assessor as today; if any check becomes `passed`, store snapshot in `_last_validated_checks`.
6. Always pass `status_reason` / `status_message` into `FrameEvent` when set.
7. Wrap unexpected exceptions in frame pipeline → `internal_error`.

Camera open/read: map to `camera_unavailable` / `camera_read_failed` with actionable messages.

WebSocket error JSON (invalid command): add `"status_reason": "protocol_error"` only if keeping client-only rule — **prefer Flutter-only** for protocol; backend may omit. Invalid command can stay message-only.

- [ ] **Step 4: Run backend tests**

```bash
cd backend
python -m pytest tests/test_phase5_status.py tests/test_rules.py tests/test_state_machine.py -v
```

Expected: PASS (no regressions).

- [ ] **Step 5: Commit (if git available)**

```bash
git add backend/schemas/frame_event.py backend/assessment/live_session.py backend/vision/camera.py backend/api/websocket.py backend/tests/test_phase5_status.py
git commit -m "feat(phase5): emit status reasons and freeze assessment while unable"
```

---

### Task 3: Flutter parse, client reasons, banner helpers (TDD)

**Files:**
- Create: `lib/core/constants/status_reasons.dart`
- Modify: `lib/services/websocket_service.dart`
- Create: `test/frame_event_parse_test.dart`
- Create: `test/status_banner_test.dart`

**Interfaces:**
- Consumes: additive JSON fields
- Produces: `FrameEventData.statusReason` / `statusMessage`; `StatusBannerInfo? resolveStatusBanner(...)`; client codes `backendDisconnected` / `protocolError`

- [ ] **Step 1: Write failing Dart tests**

`test/frame_event_parse_test.dart`:

```dart
import 'package:elixr_application/services/websocket_service.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('FrameEventData parses without optional status fields', () {
    final e = FrameEventData.fromJson({
      'movement_id': 'arm_extension',
      'assessment_state': 'calibrating',
      'body_detected': true,
      'bottle_detected': false,
      'tracking_confidence': 0.5,
      'current_step': 'calibration',
      'checks': [],
      'frame_jpeg_base64': '',
    });
    expect(e.statusReason, isNull);
    expect(e.statusMessage, isNull);
  });

  test('FrameEventData parses optional status fields', () {
    final e = FrameEventData.fromJson({
      'movement_id': 'arm_extension',
      'assessment_state': 'unable_to_assess',
      'body_detected': false,
      'bottle_detected': false,
      'tracking_confidence': 0.2,
      'current_step': 'unable_to_assess',
      'checks': [],
      'frame_jpeg_base64': '',
      'status_reason': 'low_tracking_confidence',
      'status_message': 'Improve lighting and framing.',
    });
    expect(e.statusReason, 'low_tracking_confidence');
    expect(e.statusMessage, 'Improve lighting and framing.');
  });
}
```

`test/status_banner_test.dart` — test `resolveStatusBanner` returns low-confidence copy for unable + reason; returns disconnect copy for client reason; does not use success styling when unable.

Adjust import package name to match `pubspec.yaml` `name:`.

- [ ] **Step 2: Run tests — expect failure**

```bash
flutter test test/frame_event_parse_test.dart test/status_banner_test.dart
```

- [ ] **Step 3: Implement Dart models/helpers**

Extend `FrameEventData` with optional `statusReason` / `statusMessage`.

On WS disconnect / health-fail path set client `status_reason` equivalent field or `errorMessage` + `clientStatusReason = backend_disconnected`.

On JSON parse failure of a WS message: `protocol_error`.

Implement `resolveStatusBanner` in `status_reasons.dart` prioritizing `assessment_state == unable_to_assess` then reason codes.

- [ ] **Step 4: Re-run Flutter tests — PASS**

- [ ] **Step 5: Commit (if git available)**

```bash
git add lib/core/constants/status_reasons.dart lib/services/websocket_service.dart test/frame_event_parse_test.dart test/status_banner_test.dart
git commit -m "feat(phase5): parse status reasons and resolve practice banners"
```

---

### Task 4: Soft safety + practice/camera UI polish

**Files:**
- Create: `lib/features/practice/practice_safety.dart`
- Modify: `lib/features/practice/practice_shell_screen.dart`
- Modify: `lib/features/camera_test/camera_test_screen.dart`
- Modify: `lib/core/widgets/status_chip.dart`
- Modify: `lib/features/onboarding/onboarding_screen.dart`
- Modify: `lib/features/safety/safety_screen.dart`

**Interfaces:**
- Consumes: `resolveStatusBanner`, session flag `PracticeSafetyGate`
- Produces: soft sheet before Start; animated banners/chips; updated copy

- [ ] **Step 1: Implement `PracticeSafetyGate`.**session-only**

```dart
class PracticeSafetyGate {
  static bool _suppressedThisLaunch = false;
  static bool get suppressedThisLaunch => _suppressedThisLaunch;
  static void suppressForLaunch() => _suppressedThisLaunch = true;

  static Future<void> showIfNeeded(BuildContext context) async {
    if (_suppressedThisLaunch) return;
    // showModalBottomSheet — Continue, Don't show again this launch, dismissible
  }
}
```

Wire into `_start()` **before** connecting: `await PracticeSafetyGate.showIfNeeded(context);` then proceed (even if dismissed).

- [ ] **Step 2: Practice shell banners**

Replace ad-hoc warning container with `AnimatedSwitcher` driven by `resolveStatusBanner` + existing local/WS errors. Actionable copy. While `unable_to_assess`, do not run any success animation on chips.

Label offline fallback banner as **demo fallback (not live CV)** if `_useOfflineMock` remains — do not expand onboarding claims.

Add `Semantics` on Start/Stop.

- [ ] **Step 3: StatusChip animation**

Wrap label/`Container` in `AnimatedSwitcher(duration: 200ms, child: ... key: ValueKey(status))`.

- [ ] **Step 4: Camera test + onboarding + safety copy**

- Camera test: remove “mock until Phase 3”; say live readiness checks when backend connected.
- Onboarding: live camera-based checkpoint feedback when backend is running; local storage for history; no “Phase 1 only” claim.
- Safety screen: align bullets with §20 (opaque plastic, no glass, one user, clearance, etc.).

- [ ] **Step 5: Manual smoke**

Run app against backend: open practice → soft sheet → Start → cover lens → low-confidence banner after debounce → uncover → recovery without full reset of prior passes.

- [ ] **Step 6: Commit (if git available)**

```bash
git add lib/features/practice lib/features/camera_test lib/features/onboarding lib/features/safety lib/core/widgets/status_chip.dart
git commit -m "feat(phase5): soft safety reminder and practice status UI polish"
```

---

### Task 5: Documentation + claims + demo checklist

**Files:**
- Modify: `README.md`
- Create: `backend/README_PHASE5.md`
- Modify: `backend/assessment/LIMITATIONS.md` (short Phase 5 note on confidence composite + unable freeze)
- Modify: `elixr_plan.md` frontmatter Phase 5 → completed

**Interfaces:**
- Consumes: implemented behavior from Tasks 1–4
- Produces: reproducible setup docs; four-tier claims; demo stability checklist with environment fields

- [ ] **Step 1: Replace root README**

Include: prerequisites, backend venv/install/run (`uvicorn`), Flutter Windows run, health/WS URLs from `lib/core/constants/websocket_constants.dart`, troubleshooting, links to phase READMEs + `eval/`, short Developer fallback for `ELIXR_USE_MOCK` (not primary).

- [ ] **Step 2: Write `backend/README_PHASE5.md`**

Include: confidence formula table, reason enum + priority, config knobs, freeze/resume rules, manuscript claims checklist (Implemented / Technically tested / User-evaluated / Not validated), **10-minute demo stability check** with environment blanks and practical pass conditions (camera release, duplicate connection, memory, UI responsiveness, duplicate saves, false-pass, unexpected exit).

- [ ] **Step 3: Sync LIMITATIONS + elixr_plan todo status**

- [ ] **Step 4: Commit (if git available)**

```bash
git add README.md backend/README_PHASE5.md backend/assessment/LIMITATIONS.md elixr_plan.md
git commit -m "docs(phase5): setup README, claims tiers, and demo stability checklist"
```

---

## Spec coverage checklist

| Spec item | Task |
|---|---|
| Confidence formula defined + used | 1, 2 |
| Reason enum + priority + `internal_error` | 1, 2 |
| Debounce enter/recovery | 1, 2 |
| Preserve passed; block new passes; freeze assessor | 1, 2 |
| Sequence resume without reset | 2, 4 manual |
| Soft safety continuation | 4 |
| Mock copy rules | 4, 5 |
| Animations banners/chips; no router rewrite | 4 |
| Flutter missing optional fields tests | 3 |
| Expanded backend/Flutter tests | 1–3 |
| README + PHASE5 + claims tiers + demo checklist | 5 |
| No new deps / thin polish | Global |

## Placeholder / consistency self-review

- No TBD steps; helpers named consistently (`compute_tracking_confidence`, `pick_status_reason`, `LowConfidenceGate`, `merge_checks_while_unable`).
- Commit steps gated on git availability.
- Package import in Dart tests must match `pubspec.yaml` `name` at implementation time.
