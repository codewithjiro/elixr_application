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
