import '../database/database_helper.dart';
import '../models/user.dart';

class UserRepository {
  UserRepository(this._dbHelper);

  final DatabaseHelper _dbHelper;

  Future<User?> findByUsername(String username) async {
    final db = await _dbHelper.database;
    final rows = await db.query(
      'users',
      where: 'username = ?',
      whereArgs: [username],
      limit: 1,
    );
    if (rows.isEmpty) return null;
    return User.fromMap(rows.first);
  }

  Future<User?> findById(int id) async {
    final db = await _dbHelper.database;
    final rows = await db.query(
      'users',
      where: 'id = ?',
      whereArgs: [id],
      limit: 1,
    );
    if (rows.isEmpty) return null;
    return User.fromMap(rows.first);
  }

  Future<User> create({
    required String fullName,
    required String username,
    required String passwordHash,
    required String passwordSalt,
    required String dominantHand,
  }) async {
    final db = await _dbHelper.database;
    final now = DateTime.now().toIso8601String();
    final id = await db.insert('users', {
      'full_name': fullName,
      'username': username,
      'password_hash': passwordHash,
      'password_salt': passwordSalt,
      'dominant_hand': dominantHand,
      'onboarding_complete': 0,
      'created_at': now,
    });
    return User(
      id: id,
      fullName: fullName,
      username: username,
      passwordHash: passwordHash,
      passwordSalt: passwordSalt,
      dominantHand: dominantHand,
      onboardingComplete: false,
      createdAt: DateTime.parse(now),
    );
  }

  Future<void> updateOnboardingComplete(int userId, bool complete) async {
    final db = await _dbHelper.database;
    await db.update(
      'users',
      {'onboarding_complete': complete ? 1 : 0},
      where: 'id = ?',
      whereArgs: [userId],
    );
  }

  Future<void> updateDominantHand(int userId, String hand) async {
    final db = await _dbHelper.database;
    await db.update(
      'users',
      {'dominant_hand': hand},
      where: 'id = ?',
      whereArgs: [userId],
    );
  }
}
