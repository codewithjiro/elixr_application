import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../core/constants/app_constants.dart';
import '../core/constants/status_reasons.dart';
import '../core/constants/websocket_constants.dart';

enum WsConnectionState { disconnected, connecting, connected, error }

class AssessmentCheckpoint {
  const AssessmentCheckpoint({
    required this.key,
    required this.status,
    required this.message,
    this.measuredValue,
    this.expectedRange,
  });

  final String key;
  final String status;
  final String message;
  final String? measuredValue;
  final String? expectedRange;

  String get label => key
      .split('_')
      .map((w) => w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
      .join(' ');

  /// Map backend statuses onto UI chip statuses.
  String get uiStatus {
    switch (status) {
      case 'needs_improvement':
        return AppConstants.resultPartial;
      case 'passed':
        return AppConstants.resultPassed;
      case 'failed':
        return AppConstants.resultFailed;
      case 'in_progress':
        return AppConstants.resultInProgress;
      case 'not_assessed':
        return AppConstants.resultNotAssessed;
      default:
        return status;
    }
  }

  factory AssessmentCheckpoint.fromJson(Map<String, dynamic> json) {
    final measured = json['measured_value'];
    return AssessmentCheckpoint(
      key: json['key'] as String? ?? '',
      status: json['status'] as String? ?? AppConstants.resultNotAssessed,
      message: json['message'] as String? ?? '',
      measuredValue: measured?.toString(),
      expectedRange: json['expected_range'] as String?,
    );
  }
}

class FrameEventData {
  const FrameEventData({
    required this.movementId,
    required this.assessmentState,
    required this.bodyDetected,
    required this.bottleDetected,
    required this.trackingConfidence,
    required this.currentStep,
    required this.checks,
    this.frameBytes,
    this.cameraSource,
    this.statusReason,
    this.statusMessage,
  });

  final String movementId;
  final String assessmentState;
  final bool bodyDetected;
  final bool bottleDetected;
  final double trackingConfidence;
  final String currentStep;
  final List<AssessmentCheckpoint> checks;
  final Uint8List? frameBytes;
  final String? cameraSource;
  final String? statusReason;
  final String? statusMessage;

  factory FrameEventData.fromJson(Map<String, dynamic> json) {
    Uint8List? bytes;
    final b64 = json['frame_jpeg_base64'] as String?;
    if (b64 != null && b64.isNotEmpty) {
      try {
        bytes = base64Decode(b64);
      } catch (_) {
        bytes = null;
      }
    }

    final rawChecks = json['checks'] as List<dynamic>? ?? const [];
    return FrameEventData(
      movementId: json['movement_id'] as String? ?? '',
      assessmentState: json['assessment_state'] as String? ?? '',
      bodyDetected: json['body_detected'] as bool? ?? false,
      bottleDetected: json['bottle_detected'] as bool? ?? false,
      trackingConfidence:
          (json['tracking_confidence'] as num?)?.toDouble() ?? 0,
      currentStep: json['current_step'] as String? ?? '',
      checks: rawChecks
          .whereType<Map<String, dynamic>>()
          .map(AssessmentCheckpoint.fromJson)
          .toList(),
      frameBytes: bytes,
      cameraSource: json['camera_source'] as String?,
      statusReason: json['status_reason'] as String?,
      statusMessage: json['status_message'] as String?,
    );
  }
}

class SessionSummaryData {
  const SessionSummaryData({
    required this.movementId,
    required this.resultStatus,
    required this.durationSeconds,
    required this.attemptCount,
    required this.passedCheckCount,
    required this.failedCheckCount,
    required this.notAssessedCount,
    required this.detectionInterruptions,
    required this.checks,
    this.assessmentVersion = '3.0',
    this.message,
  });

  final String movementId;
  final String resultStatus;
  final int durationSeconds;
  final int attemptCount;
  final int passedCheckCount;
  final int failedCheckCount;
  final int notAssessedCount;
  final int detectionInterruptions;
  final List<AssessmentCheckpoint> checks;
  final String assessmentVersion;
  final String? message;

  factory SessionSummaryData.fromJson(Map<String, dynamic> json) {
    final rawChecks = json['checks'] as List<dynamic>? ?? const [];
    return SessionSummaryData(
      movementId: json['movement_id'] as String? ?? '',
      resultStatus: json['result_status'] as String? ?? 'not_assessed',
      durationSeconds: (json['duration_seconds'] as num?)?.toInt() ?? 0,
      attemptCount: (json['attempt_count'] as num?)?.toInt() ?? 0,
      passedCheckCount: (json['passed_check_count'] as num?)?.toInt() ?? 0,
      failedCheckCount: (json['failed_check_count'] as num?)?.toInt() ?? 0,
      notAssessedCount: (json['not_assessed_count'] as num?)?.toInt() ?? 0,
      detectionInterruptions:
          (json['detection_interruptions'] as num?)?.toInt() ?? 0,
      assessmentVersion: json['assessment_version'] as String? ?? '3.0',
      message: json['message'] as String?,
      checks: rawChecks
          .whereType<Map<String, dynamic>>()
          .map(AssessmentCheckpoint.fromJson)
          .toList(),
    );
  }
}

/// Connects to the local FastAPI vision backend.
class WebSocketService extends ChangeNotifier {
  WebSocketService({
    this.connectTimeout = const Duration(seconds: 5),
    this.maxRetries = 3,
  });

  final Duration connectTimeout;
  final int maxRetries;

  WebSocketChannel? _channel;
  StreamSubscription? _subscription;
  Timer? _summaryTimeout;

  WsConnectionState _state = WsConnectionState.disconnected;
  String? _errorMessage;
  String? _clientStatusReason;
  FrameEventData? _latestFrame;
  SessionSummaryData? _latestSummary;
  String? _sessionMessage;
  Completer<SessionSummaryData?>? _stopCompleter;
  bool _frameNotifyScheduled = false;

  WsConnectionState get connectionState => _state;
  bool get isConnected => _state == WsConnectionState.connected;
  String? get errorMessage => _errorMessage;
  String? get clientStatusReason => _clientStatusReason;
  FrameEventData? get latestFrame => _latestFrame;
  SessionSummaryData? get latestSummary => _latestSummary;
  String? get sessionMessage => _sessionMessage;
  String get endpointUrl => WebSocketConstants.defaultUrl;
  String get healthUrl => WebSocketConstants.healthUrl;

  Future<bool> checkHealth({
    Duration timeout = const Duration(seconds: 3),
  }) async {
    try {
      final client = HttpClient();
      client.connectionTimeout = timeout;
      final request = await client.getUrl(Uri.parse(healthUrl));
      final response = await request.close().timeout(timeout);
      final body = await response.transform(utf8.decoder).join();
      client.close(force: true);
      if (response.statusCode != 200) {
        _setClientStatusReason(StatusReasons.backendDisconnected);
        return false;
      }
      final json = jsonDecode(body) as Map<String, dynamic>;
      final healthy = json['status'] == 'ok';
      _setClientStatusReason(
        healthy ? null : StatusReasons.backendDisconnected,
      );
      return healthy;
    } catch (_) {
      _setClientStatusReason(StatusReasons.backendDisconnected);
      return false;
    }
  }

  Future<void> connect() async {
    if (_state == WsConnectionState.connecting ||
        _state == WsConnectionState.connected) {
      return;
    }

    _setState(WsConnectionState.connecting, clearError: true);

    Object? lastError;
    for (var attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        final channel = WebSocketChannel.connect(Uri.parse(endpointUrl));
        await channel.ready.timeout(connectTimeout);
        _channel = channel;
        _subscription = channel.stream.listen(
          _onMessage,
          onError: (Object error) {
            _errorMessage = error.toString();
            _clientStatusReason = StatusReasons.backendDisconnected;
            _setState(WsConnectionState.error);
          },
          onDone: () {
            if (_state != WsConnectionState.disconnected) {
              _clientStatusReason = StatusReasons.backendDisconnected;
              _setState(WsConnectionState.disconnected);
            }
          },
          cancelOnError: true,
        );
        _clientStatusReason = null;
        _setState(WsConnectionState.connected, clearError: true);
        return;
      } catch (e) {
        lastError = e;
        await Future<void>.delayed(Duration(milliseconds: 400 * attempt));
      }
    }

    _errorMessage =
        'Could not connect to $endpointUrl after $maxRetries attempts. '
        'Is the backend running?\n($lastError)';
    _clientStatusReason = StatusReasons.backendDisconnected;
    _setState(WsConnectionState.error);
  }

  Future<void> disconnect() async {
    _summaryTimeout?.cancel();
    _summaryTimeout = null;
    await _subscription?.cancel();
    _subscription = null;
    await _channel?.sink.close();
    _channel = null;
    _latestFrame = null;
    _sessionMessage = null;
    _clientStatusReason = null;
    if (_stopCompleter != null && !_stopCompleter!.isCompleted) {
      _stopCompleter!.complete(null);
    }
    _stopCompleter = null;
    _setState(WsConnectionState.disconnected);
  }

  void sendMessage(Map<String, dynamic> message) {
    if (_channel == null || !isConnected) {
      _errorMessage = 'Not connected to backend';
      _clientStatusReason = StatusReasons.backendDisconnected;
      notifyListeners();
      return;
    }
    _channel!.sink.add(jsonEncode(message));
  }

  void startSession({
    required String movementId,
    String dominantHand = AppConstants.dominantHandRight,
    bool mirrorCamera = true,
  }) {
    _latestSummary = null;
    _latestFrame = null;
    _sessionMessage = null;
    sendMessage({
      'action': 'start',
      'movement_id': movementId,
      'dominant_hand': dominantHand,
      'mirror_camera': mirrorCamera,
    });
    notifyListeners();
  }

  /// Sends stop and waits for `session_summary` (or timeout).
  Future<SessionSummaryData?> stopSession({
    Duration timeout = const Duration(seconds: 4),
  }) async {
    if (!isConnected) return _latestSummary;

    _stopCompleter = Completer<SessionSummaryData?>();
    sendMessage({'action': 'stop'});

    _summaryTimeout?.cancel();
    _summaryTimeout = Timer(timeout, () {
      if (_stopCompleter != null && !_stopCompleter!.isCompleted) {
        _stopCompleter!.complete(_latestSummary);
      }
    });

    final summary = await _stopCompleter!.future;
    _summaryTimeout?.cancel();
    _stopCompleter = null;
    return summary;
  }

  Future<void> cancelSession() async {
    sendMessage({'action': 'cancel'});
    _latestFrame = null;
    notifyListeners();
  }

  void clearFrame() {
    _latestFrame = null;
    _latestSummary = null;
    _sessionMessage = null;
    notifyListeners();
  }

  void applyProtocolError(Object error) {
    _errorMessage = 'Bad message from backend: $error';
    _clientStatusReason = StatusReasons.protocolError;
    notifyListeners();
  }

  void _onMessage(dynamic raw) {
    try {
      final text = raw is String ? raw : raw.toString();
      final json = jsonDecode(text) as Map<String, dynamic>;
      _clientStatusReason = null;
      final type = json['type'] as String? ?? '';

      switch (type) {
        case 'frame':
          // Keep only the newest frame and coalesce rebuilds so a slow UI
          // decode cannot queue WebSocket frames into visible delay.
          _latestFrame = FrameEventData.fromJson(json);
          if (!_frameNotifyScheduled) {
            _frameNotifyScheduled = true;
            scheduleMicrotask(() {
              _frameNotifyScheduled = false;
              notifyListeners();
            });
          }
        case 'session_summary':
          _latestSummary = SessionSummaryData.fromJson(json);
          if (_stopCompleter != null && !_stopCompleter!.isCompleted) {
            _stopCompleter!.complete(_latestSummary);
          }
          notifyListeners();
        case 'session_started':
          _sessionMessage = json['message'] as String?;
          notifyListeners();
        case 'session_cancelled':
          _sessionMessage = 'Session cancelled';
          _latestFrame = null;
          notifyListeners();
        case 'error':
          _errorMessage = json['message'] as String? ?? 'Backend error';
          notifyListeners();
        default:
          break;
      }
    } catch (e) {
      applyProtocolError(e);
    }
  }

  void _setClientStatusReason(String? reason) {
    if (_clientStatusReason == reason) return;
    _clientStatusReason = reason;
    notifyListeners();
  }

  void _setState(WsConnectionState state, {bool clearError = false}) {
    _state = state;
    if (clearError) _errorMessage = null;
    notifyListeners();
  }

  @override
  void dispose() {
    _summaryTimeout?.cancel();
    unawaited(disconnect());
    super.dispose();
  }
}
