class StatusReasons {
  const StatusReasons._();

  static const cameraUnavailable = 'camera_unavailable';
  static const cameraReadFailed = 'camera_read_failed';
  static const modelsUnavailable = 'models_unavailable';
  static const internalError = 'internal_error';
  static const lowTrackingConfidence = 'low_tracking_confidence';
  static const bodyNotVisible = 'body_not_visible';
  static const bottleNotVisible = 'bottle_not_visible';

  // Client-only reasons; the backend does not emit these values.
  static const backendDisconnected = 'backend_disconnected';
  static const protocolError = 'protocol_error';
}

enum StatusBannerTone { success, warning, error }

class StatusBannerInfo {
  const StatusBannerInfo({required this.message, required this.tone});

  final String message;
  final StatusBannerTone tone;
}

StatusBannerInfo? resolveStatusBanner({
  String? assessmentState,
  String? statusReason,
  String? statusMessage,
  String? clientStatusReason,
}) {
  final message = statusMessage?.trim();

  if (clientStatusReason != null) {
    return StatusBannerInfo(
      message: message?.isNotEmpty == true
          ? message!
          : _messageForReason(clientStatusReason) ??
                'The session encountered a connection error.',
      tone: _errorReasons.contains(clientStatusReason)
          ? StatusBannerTone.error
          : StatusBannerTone.warning,
    );
  }

  if (assessmentState == 'unable_to_assess') {
    return StatusBannerInfo(
      message: message?.isNotEmpty == true
          ? message!
          : _messageForReason(statusReason) ??
                'Assessment paused. Check your camera view and try again.',
      tone: _errorReasons.contains(statusReason)
          ? StatusBannerTone.error
          : StatusBannerTone.warning,
    );
  }

  return null;
}

const _errorReasons = {
  StatusReasons.cameraUnavailable,
  StatusReasons.cameraReadFailed,
  StatusReasons.modelsUnavailable,
  StatusReasons.internalError,
  StatusReasons.backendDisconnected,
  StatusReasons.protocolError,
};

String? _messageForReason(String? reason) {
  switch (reason) {
    case StatusReasons.cameraUnavailable:
      return 'Camera unavailable. Check camera access and reconnect it.';
    case StatusReasons.cameraReadFailed:
      return 'Camera feed stopped. Reconnect the camera and restart.';
    case StatusReasons.modelsUnavailable:
      return 'Assessment models are unavailable. Restart the backend.';
    case StatusReasons.internalError:
      return 'Assessment stopped unexpectedly. Restart the session.';
    case StatusReasons.lowTrackingConfidence:
      return 'Improve lighting and framing, then keep your full body visible.';
    case StatusReasons.bodyNotVisible:
      return 'Stand front-facing with your full body visible in frame.';
    case StatusReasons.bottleNotVisible:
      return 'Keep the opaque practice bottle visible and improve lighting.';
    case StatusReasons.backendDisconnected:
      return 'The backend disconnected. Check that it is running and reconnect.';
    case StatusReasons.protocolError:
      return 'The backend sent an invalid message. Restart the session.';
    default:
      return null;
  }
}
