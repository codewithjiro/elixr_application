import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/constants/app_constants.dart';
import '../../core/constants/websocket_constants.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/primary_button.dart';
import '../../services/auth_service.dart';
import '../../services/session_service.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  Future<void> _exportChapter4(BuildContext context) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      final path =
          await context.read<SessionService>().exportAnonymizedChapter4Csv();
      messenger.showSnackBar(
        SnackBar(content: Text('Exported anonymized CSVs to:\n$path')),
      );
    } catch (e) {
      messenger.showSnackBar(
        SnackBar(content: Text('Export failed: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
    final user = auth.currentUser!;

    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Text('Account', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Card(
            child: Column(
              children: [
                ListTile(
                  title: const Text('Full name'),
                  subtitle: Text(user.fullName),
                ),
                const Divider(height: 1),
                ListTile(
                  title: const Text('Username'),
                  subtitle: Text(user.username),
                ),
                const Divider(height: 1),
                ListTile(
                  title: const Text('Dominant hand'),
                  subtitle: Text(user.dominantHand),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          Text('Backend', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Card(
            child: ListTile(
              title: const Text('WebSocket endpoint'),
              subtitle: Text(WebSocketConstants.defaultUrl),
              trailing: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.success.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text('Phase 3+', style: TextStyle(fontSize: 11)),
              ),
            ),
          ),
          const SizedBox(height: 24),
          Text(
            'Chapter 4 export',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Card(
            child: ListTile(
              title: const Text('Export anonymized results'),
              subtitle: const Text(
                'Writes session and checkpoint CSVs with no username or images.',
              ),
              trailing: const Icon(Icons.download_outlined),
              onTap: () => _exportChapter4(context),
            ),
          ),
          const SizedBox(height: 32),
          PrimaryButton(
            label: 'Log Out',
            onPressed: () async {
              await auth.logout();
              if (context.mounted) context.go('/login');
            },
          ),
          const SizedBox(height: 16),
          Text(
            '${AppConstants.appName} · Phase 4 persistence & evaluation',
            style: Theme.of(context).textTheme.bodySmall,
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}
