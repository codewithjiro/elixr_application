import 'package:elixr_application/core/constants/status_reasons.dart';
import 'package:elixr_application/services/websocket_service.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('completed state ignores a stale server warning', () {
    final banner = resolveStatusBanner(
      assessmentState: 'completed',
      statusReason: StatusReasons.lowTrackingConfidence,
    );

    expect(banner, isNull);
  });

  test('calibrating state ignores status message alone', () {
    final banner = resolveStatusBanner(
      assessmentState: 'calibrating',
      statusMessage: 'Improve lighting and framing.',
    );

    expect(banner, isNull);
  });

  test('unable low confidence resolves actionable warning copy', () {
    final banner = resolveStatusBanner(
      assessmentState: 'unable_to_assess',
      statusReason: StatusReasons.lowTrackingConfidence,
    );

    expect(banner, isNotNull);
    expect(banner!.message, contains('lighting'));
    expect(banner.tone, StatusBannerTone.warning);
  });

  test('unable camera unavailable resolves error tone', () {
    final banner = resolveStatusBanner(
      assessmentState: 'unable_to_assess',
      statusReason: StatusReasons.cameraUnavailable,
    );

    expect(banner, isNotNull);
    expect(banner!.message, contains('Camera'));
    expect(banner.tone, StatusBannerTone.error);
  });

  test('unable models unavailable resolves error tone', () {
    final banner = resolveStatusBanner(
      assessmentState: 'unable_to_assess',
      statusReason: StatusReasons.modelsUnavailable,
    );

    expect(banner, isNotNull);
    expect(banner!.message, contains('models'));
    expect(banner.tone, StatusBannerTone.error);
  });

  test('client disconnect resolves actionable error copy', () {
    final banner = resolveStatusBanner(
      assessmentState: 'movement_in_progress',
      clientStatusReason: StatusReasons.backendDisconnected,
    );

    expect(banner, isNotNull);
    expect(banner!.message, contains('backend'));
    expect(banner.tone, StatusBannerTone.error);
  });

  test('unable state never resolves success styling', () {
    final banner = resolveStatusBanner(
      assessmentState: 'unable_to_assess',
      statusMessage: 'Assessment paused.',
    );

    expect(banner, isNotNull);
    expect(banner!.tone, isNot(StatusBannerTone.success));
  });

  test('protocol errors set the client protocol reason', () {
    final service = WebSocketService();

    service.applyProtocolError(const FormatException('invalid JSON'));

    expect(service.clientStatusReason, StatusReasons.protocolError);
    expect(service.errorMessage, contains('invalid JSON'));
  });
}
