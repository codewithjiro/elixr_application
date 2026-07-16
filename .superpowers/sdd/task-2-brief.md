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
