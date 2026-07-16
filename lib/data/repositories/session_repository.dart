import '../database/database_helper.dart';
import '../models/practice_session.dart';
import '../models/session_check.dart';

class SessionRepository {
  SessionRepository(this._dbHelper);

  final DatabaseHelper _dbHelper;

  Future<List<PracticeSession>> getSessionsForUser(int userId) async {
    final db = await _dbHelper.database;
    final rows = await db.query(
      'sessions',
      where: 'user_id = ?',
      whereArgs: [userId],
      orderBy: 'created_at DESC',
    );
    return rows.map(PracticeSession.fromMap).toList();
  }

  Future<PracticeSession?> getSessionById(int id) async {
    final db = await _dbHelper.database;
    final rows = await db.query(
      'sessions',
      where: 'id = ?',
      whereArgs: [id],
      limit: 1,
    );
    if (rows.isEmpty) return null;
    return PracticeSession.fromMap(rows.first);
  }

  Future<List<SessionCheck>> getChecksForSession(int sessionId) async {
    final db = await _dbHelper.database;
    final rows = await db.query(
      'session_checks',
      where: 'session_id = ?',
      whereArgs: [sessionId],
      orderBy: 'created_at ASC',
    );
    return rows.map(SessionCheck.fromMap).toList();
  }

  Future<PracticeSession> createSession(PracticeSession session) async {
    final db = await _dbHelper.database;
    final map = Map<String, dynamic>.from(session.toMap())..remove('id');
    final id = await db.insert('sessions', map);
    return PracticeSession(
      id: id,
      userId: session.userId,
      movementId: session.movementId,
      resultStatus: session.resultStatus,
      durationSeconds: session.durationSeconds,
      attemptCount: session.attemptCount,
      passedCheckCount: session.passedCheckCount,
      failedCheckCount: session.failedCheckCount,
      notAssessedCount: session.notAssessedCount,
      detectionInterruptions: session.detectionInterruptions,
      assessmentVersion: session.assessmentVersion,
      createdAt: session.createdAt,
    );
  }

  Future<void> insertCheck(SessionCheck check) async {
    final db = await _dbHelper.database;
    final map = Map<String, dynamic>.from(check.toMap())..remove('id');
    await db.insert('session_checks', map);
  }

  Future<int> sessionCountForUser(int userId) async {
    final db = await _dbHelper.database;
    final result = await db.rawQuery(
      'SELECT COUNT(*) as count FROM sessions WHERE user_id = ?',
      [userId],
    );
    return result.first['count'] as int? ?? 0;
  }

  /// Completed sessions + pass/fail/partial counts grouped by movement.
  Future<List<Map<String, Object?>>> movementStatsForUser(int userId) async {
    final db = await _dbHelper.database;
    return db.rawQuery(
      '''
      SELECT
        movement_id,
        COUNT(*) AS session_count,
        SUM(CASE WHEN result_status = 'passed' THEN 1 ELSE 0 END) AS passed_sessions,
        SUM(CASE WHEN result_status = 'failed' THEN 1 ELSE 0 END) AS failed_sessions,
        SUM(CASE WHEN result_status = 'partial' THEN 1 ELSE 0 END) AS partial_sessions,
        SUM(passed_check_count) AS passed_checks,
        SUM(failed_check_count) AS failed_checks
      FROM sessions
      WHERE user_id = ?
      GROUP BY movement_id
      ORDER BY session_count DESC
      ''',
      [userId],
    );
  }

  /// Most common failed checkpoints across the user's sessions.
  Future<List<Map<String, Object?>>> commonFailedCheckpoints(
    int userId, {
    int limit = 10,
  }) async {
    final db = await _dbHelper.database;
    return db.rawQuery(
      '''
      SELECT
        c.checkpoint_key,
        c.checkpoint_label,
        COUNT(*) AS fail_count
      FROM session_checks c
      INNER JOIN sessions s ON s.id = c.session_id
      WHERE s.user_id = ?
        AND c.result_status = 'failed'
      GROUP BY c.checkpoint_key, c.checkpoint_label
      ORDER BY fail_count DESC
      LIMIT ?
      ''',
      [userId, limit],
    );
  }

  Future<List<SessionCheck>> getAllChecksForUser(int userId) async {
    final db = await _dbHelper.database;
    final rows = await db.rawQuery(
      '''
      SELECT c.*
      FROM session_checks c
      INNER JOIN sessions s ON s.id = c.session_id
      WHERE s.user_id = ?
      ORDER BY c.created_at ASC
      ''',
      [userId],
    );
    return rows.map(SessionCheck.fromMap).toList();
  }
}
