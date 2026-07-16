import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '../core/constants/app_constants.dart';
import '../data/models/practice_session.dart';
import '../data/models/session_check.dart';
import '../data/repositories/session_repository.dart';
import 'auth_service.dart';

class MovementProgressStat {
  const MovementProgressStat({
    required this.movementId,
    required this.sessionCount,
    required this.passedSessions,
    required this.failedSessions,
    required this.partialSessions,
    required this.passedChecks,
    required this.failedChecks,
  });

  final String movementId;
  final int sessionCount;
  final int passedSessions;
  final int failedSessions;
  final int partialSessions;
  final int passedChecks;
  final int failedChecks;
}

class FailedCheckpointStat {
  const FailedCheckpointStat({
    required this.checkpointKey,
    required this.checkpointLabel,
    required this.failCount,
  });

  final String checkpointKey;
  final String checkpointLabel;
  final int failCount;
}

class SessionService extends ChangeNotifier {
  SessionService(this._sessionRepo, this._authService);

  final SessionRepository _sessionRepo;
  final AuthService _authService;

  List<PracticeSession> _sessions = [];
  List<MovementProgressStat> _movementStats = [];
  List<FailedCheckpointStat> _commonFailed = [];
  bool _loading = false;

  List<PracticeSession> get sessions => _sessions;
  List<MovementProgressStat> get movementStats => _movementStats;
  List<FailedCheckpointStat> get commonFailedCheckpoints => _commonFailed;
  bool get loading => _loading;

  Future<void> loadSessions() async {
    final user = _authService.currentUser;
    if (user == null) {
      _sessions = [];
      notifyListeners();
      return;
    }

    _loading = true;
    notifyListeners();

    _sessions = await _sessionRepo.getSessionsForUser(user.id);
    final stats = await _sessionRepo.movementStatsForUser(user.id);
    _movementStats = stats
        .map(
          (row) => MovementProgressStat(
            movementId: row['movement_id'] as String,
            sessionCount: row['session_count'] as int? ?? 0,
            passedSessions: row['passed_sessions'] as int? ?? 0,
            failedSessions: row['failed_sessions'] as int? ?? 0,
            partialSessions: row['partial_sessions'] as int? ?? 0,
            passedChecks: row['passed_checks'] as int? ?? 0,
            failedChecks: row['failed_checks'] as int? ?? 0,
          ),
        )
        .toList();
    final failed = await _sessionRepo.commonFailedCheckpoints(user.id);
    _commonFailed = failed
        .map(
          (row) => FailedCheckpointStat(
            checkpointKey: row['checkpoint_key'] as String,
            checkpointLabel: row['checkpoint_label'] as String,
            failCount: row['fail_count'] as int? ?? 0,
          ),
        )
        .toList();
    _loading = false;
    notifyListeners();
  }

  Future<PracticeSession?> getSession(int id) =>
      _sessionRepo.getSessionById(id);

  Future<List<SessionCheck>> getChecks(int sessionId) =>
      _sessionRepo.getChecksForSession(sessionId);

  Future<int> sessionCount() async {
    final user = _authService.currentUser;
    if (user == null) return 0;
    return _sessionRepo.sessionCountForUser(user.id);
  }

  /// Creates a mock completed session for offline demo fallback.
  Future<PracticeSession> saveMockSession({
    required String movementId,
    required int durationSeconds,
  }) async {
    final user = _authService.currentUser!;
    final session = PracticeSession(
      id: 0,
      userId: user.id,
      movementId: movementId,
      resultStatus: AppConstants.resultPartial,
      durationSeconds: durationSeconds,
      attemptCount: 1,
      passedCheckCount: 1,
      failedCheckCount: 1,
      notAssessedCount: 2,
      detectionInterruptions: 0,
      assessmentVersion: '1.0-mock',
      createdAt: DateTime.now(),
    );

    final saved = await _sessionRepo.createSession(session);

    final mockChecks = [
      SessionCheck(
        id: 0,
        sessionId: saved.id,
        checkpointKey: 'stance',
        checkpointLabel: 'Stance Check',
        resultStatus: AppConstants.resultPassed,
        measuredValue: '0.42m',
        expectedRange: '0.35–0.50m',
        confidence: 0.87,
        message: 'MOCK — good stance',
        createdAt: DateTime.now(),
      ),
      SessionCheck(
        id: 0,
        sessionId: saved.id,
        checkpointKey: 'extension',
        checkpointLabel: 'Arm Extension',
        resultStatus: AppConstants.resultFailed,
        measuredValue: '62°',
        expectedRange: '70–90°',
        confidence: 0.72,
        message: 'MOCK — extend further',
        createdAt: DateTime.now(),
      ),
    ];

    for (final check in mockChecks) {
      await _sessionRepo.insertCheck(check);
    }

    await loadSessions();
    return saved;
  }

  /// Persists a backend session_summary (Phase 2+).
  Future<PracticeSession> saveBackendSession({
    required String movementId,
    required String resultStatus,
    required int durationSeconds,
    required int attemptCount,
    required int passedCheckCount,
    required int failedCheckCount,
    required int notAssessedCount,
    required int detectionInterruptions,
    required String assessmentVersion,
    required List<SessionCheck> checks,
  }) async {
    final user = _authService.currentUser!;
    final mappedStatus = switch (resultStatus) {
      'completed' => AppConstants.resultPassed,
      'partial' => AppConstants.resultPartial,
      'cancelled' => AppConstants.resultNotAssessed,
      'failed' => AppConstants.resultFailed,
      _ => resultStatus,
    };

    final session = PracticeSession(
      id: 0,
      userId: user.id,
      movementId: movementId,
      resultStatus: mappedStatus,
      durationSeconds: durationSeconds,
      attemptCount: attemptCount,
      passedCheckCount: passedCheckCount,
      failedCheckCount: failedCheckCount,
      notAssessedCount: notAssessedCount,
      detectionInterruptions: detectionInterruptions,
      assessmentVersion: assessmentVersion,
      createdAt: DateTime.now(),
    );

    final saved = await _sessionRepo.createSession(session);

    for (final check in checks) {
      await _sessionRepo.insertCheck(
        SessionCheck(
          id: 0,
          sessionId: saved.id,
          checkpointKey: check.checkpointKey,
          checkpointLabel: check.checkpointLabel,
          resultStatus: check.resultStatus,
          measuredValue: check.measuredValue,
          expectedRange: check.expectedRange,
          confidence: check.confidence,
          message: check.message,
          createdAt: DateTime.now(),
        ),
      );
    }

    await loadSessions();
    return saved;
  }

  /// Writes anonymized session + checkpoint CSVs (no username/images).
  /// Returns the directory path containing the files.
  Future<String> exportAnonymizedChapter4Csv() async {
    final user = _authService.currentUser;
    if (user == null) {
      throw StateError('No signed-in user');
    }

    final dir = await getApplicationDocumentsDirectory();
    final outDir = Directory(p.join(dir.path, 'elixr_exports'));
    if (!await outDir.exists()) {
      await outDir.create(recursive: true);
    }

    final stamp = DateTime.now().toIso8601String().replaceAll(':', '-');
    final sessionsPath = p.join(outDir.path, 'sessions_$stamp.csv');
    final checksPath = p.join(outDir.path, 'session_checks_$stamp.csv');

    final sessions = await _sessionRepo.getSessionsForUser(user.id);
    final checks = await _sessionRepo.getAllChecksForUser(user.id);

    final sessionsBuf = StringBuffer(
      'session_anon_id,movement_id,result_status,duration_seconds,'
      'attempt_count,passed_check_count,failed_check_count,'
      'not_assessed_count,detection_interruptions,assessment_version,created_at\n',
    );
    for (final s in sessions) {
      sessionsBuf.writeln(
        [
          s.id,
          s.movementId,
          s.resultStatus,
          s.durationSeconds,
          s.attemptCount,
          s.passedCheckCount,
          s.failedCheckCount,
          s.notAssessedCount,
          s.detectionInterruptions,
          s.assessmentVersion,
          s.createdAt.toIso8601String(),
        ].map(_csvCell).join(','),
      );
    }
    await File(sessionsPath).writeAsString(sessionsBuf.toString());

    final checksBuf = StringBuffer(
      'session_anon_id,checkpoint_key,checkpoint_label,result_status,'
      'measured_value,expected_range,confidence,message,created_at\n',
    );
    for (final c in checks) {
      checksBuf.writeln(
        [
          c.sessionId,
          c.checkpointKey,
          c.checkpointLabel,
          c.resultStatus,
          c.measuredValue ?? '',
          c.expectedRange ?? '',
          c.confidence?.toString() ?? '',
          c.message ?? '',
          c.createdAt.toIso8601String(),
        ].map(_csvCell).join(','),
      );
    }
    await File(checksPath).writeAsString(checksBuf.toString());

    return outDir.path;
  }

  static String _csvCell(Object? value) {
    final text = value?.toString() ?? '';
    if (text.contains(',') || text.contains('"') || text.contains('\n')) {
      return '"${text.replaceAll('"', '""')}"';
    }
    return text;
  }
}