import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';
import 'services/auth_service.dart';

class ElixrApp extends StatefulWidget {
  const ElixrApp({super.key});

  @override
  State<ElixrApp> createState() => _ElixrAppState();
}

class _ElixrAppState extends State<ElixrApp> {
  late final GoRouter _router;

  @override
  void initState() {
    super.initState();
    final authService = context.read<AuthService>();
    _router = AppRouter.create(authService);
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'ELIXR',
      theme: AppTheme.dark,
      routerConfig: _router,
      debugShowCheckedModeBanner: false,
    );
  }
}
