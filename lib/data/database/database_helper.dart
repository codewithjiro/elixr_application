import 'package:path/path.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import '../../core/constants/app_constants.dart';
import 'migrations.dart';

class DatabaseHelper {
  DatabaseHelper();

  Database? _database;

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDatabase();
    return _database!;
  }

  Future<Database> _initDatabase() async {
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, AppConstants.dbName);

    return openDatabase(
      path,
      version: Migrations.version,
      onCreate: (db, version) async {
        for (final script in Migrations.scripts) {
          await db.execute(script);
        }
      },
    );
  }
}
