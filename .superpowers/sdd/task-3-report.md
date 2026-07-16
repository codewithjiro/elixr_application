# Task 3 Report: Flutter Status Reasons and Banner Helpers

## Status

Completed the Flutter-only Task 3 scope. No practice or camera-test UI wiring was added.

## TDD evidence

1. Added `test/frame_event_parse_test.dart` and `test/status_banner_test.dart` first.
2. Ran:
   `flutter test test/frame_event_parse_test.dart test/status_banner_test.dart`
3. Confirmed the expected RED result: compilation failed because
   `FrameEventData.statusReason`, `FrameEventData.statusMessage`,
   `StatusReasons`, `StatusBannerInfo`, and `resolveStatusBanner` did not exist.
4. Added a disconnected-send test and confirmed it failed because
   `WebSocketService.clientStatusReason` did not exist.
5. Implemented the minimum model, client-reason, and resolver behavior.
6. Re-ran the targeted tests and confirmed all 6 passed.

## Changes

- Added optional `statusReason` and `statusMessage` fields to
  `FrameEventData`, parsed from `status_reason` and `status_message`.
- Added backend reason constants and the client-only
  `backend_disconnected` / `protocol_error` constants.
- Added `StatusBannerInfo`, `StatusBannerTone`, and
  `resolveStatusBanner`.
- The resolver prioritizes `unable_to_assess`, uses actionable backend
  messages when supplied, falls back to reason-specific copy, and never
  assigns success styling to an unable state.
- Added `WebSocketService.clientStatusReason`.
- Set `backend_disconnected` for health failures, connection failures,
  unexpected socket errors/closure, and sends while disconnected.
- Set `protocol_error` when an incoming WebSocket payload cannot be
  decoded as the expected JSON map.
- Clear the client reason after a healthy check, successful connection,
  valid inbound message, or intentional disconnect.

## Verification

- Targeted tests:
  `flutter test test/frame_event_parse_test.dart test/status_banner_test.dart`
  — 6 passed.
- Full suite: `flutter test` — 7 passed.
- Static analysis: `flutter analyze` — no issues found.
- IDE diagnostics on all four implementation/test files — no errors.

## Self-review

- Scope stayed limited to the four files named in the brief plus this report.
- Existing WebSocket behavior and public frame fields remain backward compatible.
- Banner data is Flutter-widget independent so Task 4 can choose its own rendering.
- The malformed-message mapping is exposed through
  `applyProtocolError(Object error)` and directly unit-tested without socket
  injection. Frame parsing, disconnected-client mapping, resolver priority,
  copy, and tone are covered.

## Git

No repository was initialized and no commits were created, as instructed.

## Important review fixes

- Updated `resolveStatusBanner` so healthy lifecycle states ignore stale server
  reasons and standalone status messages.
- Server reason/message banners now require `unable_to_assess`.
- Added a separate `clientStatusReason` input so connection and protocol errors
  remain visible independently of assessment lifecycle state.
- Extracted `WebSocketService.applyProtocolError(Object error)` and routed
  malformed inbound messages through it for direct unit coverage.
- Added regression tests for completed/stale warning, calibrating/message-only,
  unable/low-confidence, client disconnect, and protocol-error behavior.

Verification:
`flutter test test/frame_event_parse_test.dart test/status_banner_test.dart`
— 9 passed.
