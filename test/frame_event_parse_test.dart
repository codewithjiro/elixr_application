import 'package:elixr_application/services/websocket_service.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('FrameEventData parses without optional status fields', () {
    final event = FrameEventData.fromJson({
      'movement_id': 'arm_extension',
      'assessment_state': 'calibrating',
      'body_detected': true,
      'bottle_detected': false,
      'tracking_confidence': 0.5,
      'current_step': 'calibration',
      'checks': [],
      'frame_jpeg_base64': '',
    });

    expect(event.statusReason, isNull);
    expect(event.statusMessage, isNull);
  });

  test('FrameEventData parses optional status fields', () {
    final event = FrameEventData.fromJson({
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

    expect(event.statusReason, 'low_tracking_confidence');
    expect(event.statusMessage, 'Improve lighting and framing.');
  });

  test('sending while disconnected sets the client disconnect reason', () {
    final service = WebSocketService();

    service.sendMessage({'action': 'start'});

    expect(service.clientStatusReason, 'backend_disconnected');
  });
}
