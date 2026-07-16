class Migrations {
  static const version = 1;

  static const createUsers = '''
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  full_name TEXT NOT NULL,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  password_salt TEXT NOT NULL,
  dominant_hand TEXT NOT NULL CHECK(dominant_hand IN ('left', 'right')),
  onboarding_complete INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
)
''';

  static const createSessions = '''
CREATE TABLE sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  movement_id TEXT NOT NULL,
  result_status TEXT NOT NULL,
  duration_seconds INTEGER NOT NULL DEFAULT 0,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  passed_check_count INTEGER NOT NULL DEFAULT 0,
  failed_check_count INTEGER NOT NULL DEFAULT 0,
  not_assessed_count INTEGER NOT NULL DEFAULT 0,
  detection_interruptions INTEGER NOT NULL DEFAULT 0,
  assessment_version TEXT NOT NULL DEFAULT '1.0',
  created_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users (id)
)
''';

  static const createSessionChecks = '''
CREATE TABLE session_checks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  checkpoint_key TEXT NOT NULL,
  checkpoint_label TEXT NOT NULL,
  result_status TEXT NOT NULL,
  measured_value TEXT,
  expected_range TEXT,
  confidence REAL,
  message TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES sessions (id)
)
''';

  static const createAppSettings = '''
CREATE TABLE app_settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
)
''';

  static List<String> get scripts => [
        createUsers,
        createSessions,
        createSessionChecks,
        createAppSettings,
      ];
}
