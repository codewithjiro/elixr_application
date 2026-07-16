import 'dart:io';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'app.dart';
import 'data/database/database_helper.dart';
import 'data/repositories/session_repository.dart';
import 'data/repositories/settings_repository.dart';
import 'data/repositories/user_repository.dart';
import 'services/auth_service.dart';
import 'services/practice_service.dart';
import 'services/session_service.dart';
import 'services/websocket_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  }

  final dbHelper = DatabaseHelper();
  await dbHelper.database;

  final userRepo = UserRepository(dbHelper);
  final sessionRepo = SessionRepository(dbHelper);
  final settingsRepo = SettingsRepository(dbHelper);

  final authService = AuthService(userRepo, settingsRepo);
  await authService.init();

  final sessionService = SessionService(sessionRepo, authService);

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthService>.value(value: authService),
        ChangeNotifierProvider<SessionService>.value(value: sessionService),
        Provider<UserRepository>.value(value: userRepo),
        Provider<SessionRepository>.value(value: sessionRepo),
        Provider<SettingsRepository>.value(value: settingsRepo),
        Provider<PracticeService>(create: (_) => PracticeService()),
        ChangeNotifierProvider<WebSocketService>(
          create: (_) => WebSocketService(),
        ),
      ],
      child: const ElixrApp(),
    ),
  );
}
