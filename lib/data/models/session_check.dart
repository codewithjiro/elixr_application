class SessionCheck {
  const SessionCheck({
    required this.id,
    required this.sessionId,
    required this.checkpointKey,
    required this.checkpointLabel,
    required this.resultStatus,
    this.measuredValue,
    this.expectedRange,
    this.confidence,
    this.message,
    required this.createdAt,
  });

  final int id;
  final int sessionId;
  final String checkpointKey;
  final String checkpointLabel;
  final String resultStatus;
  final String? measuredValue;
  final String? expectedRange;
  final double? confidence;
  final String? message;
  final DateTime createdAt;

  factory SessionCheck.fromMap(Map<String, dynamic> map) {
    return SessionCheck(
      id: map['id'] as int,
      sessionId: map['session_id'] as int,
      checkpointKey: map['checkpoint_key'] as String,
      checkpointLabel: map['checkpoint_label'] as String,
      resultStatus: map['result_status'] as String,
      measuredValue: map['measured_value'] as String?,
      expectedRange: map['expected_range'] as String?,
      confidence: map['confidence'] != null
          ? (map['confidence'] as num).toDouble()
          : null,
      message: map['message'] as String?,
      createdAt: DateTime.parse(map['created_at'] as String),
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'session_id': sessionId,
      'checkpoint_key': checkpointKey,
      'checkpoint_label': checkpointLabel,
      'result_status': resultStatus,
      'measured_value': measuredValue,
      'expected_range': expectedRange,
      'confidence': confidence,
      'message': message,
      'created_at': createdAt.toIso8601String(),
    };
  }
}
