class PracticeSession {
  const PracticeSession({
    required this.id,
    required this.userId,
    required this.movementId,
    required this.resultStatus,
    required this.durationSeconds,
    required this.attemptCount,
    required this.passedCheckCount,
    required this.failedCheckCount,
    required this.notAssessedCount,
    required this.detectionInterruptions,
    required this.assessmentVersion,
    required this.createdAt,
  });

  final int id;
  final int userId;
  final String movementId;
  final String resultStatus;
  final int durationSeconds;
  final int attemptCount;
  final int passedCheckCount;
  final int failedCheckCount;
  final int notAssessedCount;
  final int detectionInterruptions;
  final String assessmentVersion;
  final DateTime createdAt;

  factory PracticeSession.fromMap(Map<String, dynamic> map) {
    return PracticeSession(
      id: map['id'] as int,
      userId: map['user_id'] as int,
      movementId: map['movement_id'] as String,
      resultStatus: map['result_status'] as String,
      durationSeconds: map['duration_seconds'] as int,
      attemptCount: map['attempt_count'] as int,
      passedCheckCount: map['passed_check_count'] as int,
      failedCheckCount: map['failed_check_count'] as int,
      notAssessedCount: map['not_assessed_count'] as int,
      detectionInterruptions: map['detection_interruptions'] as int,
      assessmentVersion: map['assessment_version'] as String,
      createdAt: DateTime.parse(map['created_at'] as String),
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'user_id': userId,
      'movement_id': movementId,
      'result_status': resultStatus,
      'duration_seconds': durationSeconds,
      'attempt_count': attemptCount,
      'passed_check_count': passedCheckCount,
      'failed_check_count': failedCheckCount,
      'not_assessed_count': notAssessedCount,
      'detection_interruptions': detectionInterruptions,
      'assessment_version': assessmentVersion,
      'created_at': createdAt.toIso8601String(),
    };
  }
}
