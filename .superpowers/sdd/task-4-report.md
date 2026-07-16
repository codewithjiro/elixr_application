# Task 4 Report — Soft safety + practice/camera UI polish

## Status

Implemented.

## Changes

- Added `PracticeSafetyGate`, shown only from practice Start. Continue and dismiss both proceed; “Don’t show again this launch” uses an in-memory static flag only.
- Replaced the practice warning block with a 200 ms `AnimatedSwitcher` banner driven by `resolveStatusBanner`, local errors, and WebSocket errors/messages.
- Labeled offline operation as “Demo fallback” and explicitly stated that checkpoints are simulated, not live CV.
- Added Start/Stop semantics and disabled success-status transitions while assessment is `unable_to_assess`.
- Added the 200 ms keyed `AnimatedSwitcher` cross-fade to `StatusChip`.
- Updated camera-test and onboarding copy to describe live assessment when the backend is running and local history storage.
- Updated the Safety guide to match the operational limits: one user, front-facing stable camera, full-body visibility, lighting, opaque plastic bottle, no glass, clear area, controlled movements, and stopping on pain/fatigue.
- Added widget coverage for launch-only safety suppression and status-chip cross-fading.

## Verification

- `flutter analyze` — passed, no issues.
- `flutter test` — passed, 12 tests.
- IDE diagnostics for edited Dart files — no errors.
- Self-review found and fixed an async mounted-state guard after the backend health check and made the front-facing camera requirement explicit.

## Git

No repository/commit requested; commits: none.

## Concerns / follow-up

- The backend-and-camera manual smoke flow was not run in this environment. It still needs physical verification of cover-lens debounce, recovery, and preservation of prior passed checkpoints.

---

## Review fixes (Important/Minor)

### Status

Implemented.

### Changes

- Added onboarding **Practice setup** step (step 3 of 4) with concise §20 bullets: one user, front-facing stable camera, full body visible, sufficient lighting, clear area, opaque plastic bottle (no glass).
- Extended camera-test helper text with the same operational constraints (short inline copy, not a Safety Guide clone).
- Added `PracticeSafetyGate.resetForTests()` (`@visibleForTesting`) to clear `_suppressedThisLaunch`; wired `setUp`/`tearDown` in `test/task4_ui_test.dart`.

### Verification

- `flutter analyze` — passed, no issues.
- `flutter test` — passed, 12 tests.

### Manual verification (not run)

- Physical camera smoke (cover-lens debounce, recovery, prior-passed preservation) remains for human verification; not claimed in this pass.
