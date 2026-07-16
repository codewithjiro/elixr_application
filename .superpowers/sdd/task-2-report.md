# Task 2 Report: FrameEvent Schema and Live Session Wiring

## Status

Completed. No Git repository was initialized and no commits were created.

## Changes

- Added optional `status_reason` and `status_message` fields to `FrameEvent`.
- Replaced live-session inline confidence calculation with `compute_tracking_confidence`.
- Added a session-owned `LowConfidenceGate` using the Phase 5 configuration values.
- Added `should_freeze_assessor` and used it to prevent assessor updates during low-confidence and hard-unavailable states.
- Preserved the latest validated checkpoint snapshot and merged it into unable-state output without promoting new checks to `passed`.
- Added prioritized status reasons and actionable messages for camera open/read failures, model failures, low confidence, body/bottle visibility, and unexpected pipeline exceptions.
- Wrapped unexpected frame-pipeline exceptions as `internal_error` frame events.
- Left WebSocket invalid-command responses unchanged, keeping `protocol_error` Flutter-only as directed.
- No camera or WebSocket source changes were needed.

## TDD Evidence

1. Added the `FrameEvent` optional-field tests.
2. Ran `python -m pytest tests/test_phase5_status.py -v`; the set-field test failed because `FrameEvent.status_reason` did not exist.
3. Added the two schema fields and reran the test file; all 7 tests passed.
4. Added the `should_freeze_assessor` truth-table test.
5. Reran the test file; collection failed because the helper did not exist.
6. Added the helper and reran the test file; all 8 tests passed.

The active Python environment initially lacked the already-declared `pydantic` dependency. Installed `pydantic>=2.7.0` locally without changing `requirements.txt`.

## Verification

- Required regression command:
  - `python -m pytest tests/test_phase5_status.py tests/test_rules.py tests/test_state_machine.py -v`
  - Result: 19 passed.
- Full backend suite:
  - `python -m pytest -v`
  - Result: 26 passed.
- IDE diagnostics on all three edited Python files: no errors.

## Self-Review

- Confirmed the assessor update call occurs only after the freeze branches.
- Confirmed recovery resumes the existing assessor instance without resetting its sequence.
- Confirmed hard-failure reason selection uses the required priority helper.
- Confirmed every emitted live frame path supplies optional reason/message values when applicable.
- Confirmed changes are limited to the requested schema, session, tests, and this report.

## Concerns

Automated tests do not exercise physical camera disconnection or local model-load failures. Those paths are mapped and guarded in code, but should also be checked during the Phase 5 manual demo-stability pass.

## Important Finding Fixes — 2026-07-15

- Changed transient camera read failure handling to release only the camera capture. Pose, YOLO, calibration, assessor state, and validated checkpoints remain intact.
- Added `_ensure_camera()` before each frame read so a session with a failed or unavailable camera retries opening it and resumes the existing assessment state after recovery.
- Added `update_validated_checks(previous, current)` and applied it to readiness, calibration, and live-assessment frames. Passed checkpoint keys now accumulate for the session instead of being replaced by the latest frame.
- Extended `tests/test_phase5_status.py` with cumulative checkpoint and camera-read state-preservation regressions. The existing freeze-helper truth-table test remains in place.
- TDD red result: the focused test file initially failed collection because `update_validated_checks` did not exist.
- No Git repository was initialized and no commit was created.

### Verification

Command:

`cd backend && python -m pytest tests/test_phase5_status.py tests/test_rules.py tests/test_state_machine.py -v`

Output summary:

`21 passed in 4.16s` (exit code 0).

IDE diagnostics reported no linter errors in `assessment/live_session.py` or `tests/test_phase5_status.py`.

### Remaining concern

Physical disconnect/reconnect behavior still requires the planned manual webcam demo-stability check; the unit regression verifies that a failed read preserves in-memory assessor and calibration state.

## Model-Load Retry Fix — 2026-07-15

- Added `_ensure_models()` to retry `_init_models()` on every frame when `_models_ok` is false or pose/YOLO handles are missing.
- Wired `_ensure_models()` at the start of `_next_frame_event` (after `_ensure_camera()`), so a session can recover from transient model-load failures without closing the WebSocket session.
- On retry success, the normal pipeline resumes and hard-unavailable (`models_unavailable`) clears automatically; assessor, calibration, and validated checkpoints are not reset.
- On retry failure, only `_models_ok` stays false and `detection_interruptions` increments — existing assessor state is preserved.
- Added `test_model_init_retry_preserves_assessor_state` using a mock-friendly `_init_models` override on a bare session instance.

### Verification

Command:

`cd backend && python -m pytest tests/test_phase5_status.py tests/test_rules.py tests/test_state_machine.py -v`

Output summary:

`22 passed in 3.28s` (exit code 0).

- Removed duplicate `test_model_init_retry_preserves_assessor_state` from `tests/test_phase5_status.py`; focused run: 11 passed.
