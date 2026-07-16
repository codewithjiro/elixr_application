import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import '../database/database_helper.dart';

class SettingsRepository {
  SettingsRepository(this._dbHelper);

  final DatabaseHelper _dbHelper;

  Future<String?> get(String key) async {
    final db = await _dbHelper.database;
    final rows = await db.query(
      'app_settings',
      where: 'key = ?',
      whereArgs: [key],
      limit: 1,
    );
    if (rows.isEmpty) return null;
    return rows.first['value'] as String?;
  }

  Future<void> set(String key, String value) async {
    final db = await _dbHelper.database;
    await db.insert(
      'app_settings',
      {'key': key, 'value': value},
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<void> remove(String key) async {
    final db = await _dbHelper.database;
    await db.delete(
      'app_settings',
      where: 'key = ?',
      whereArgs: [key],
    );
  }
}
