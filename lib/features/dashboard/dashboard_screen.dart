import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/constants/movement_catalog.dart';
import '../../core/theme/app_theme.dart';
import '../../services/auth_service.dart';
import '../../services/session_service.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<SessionService>().loadSessions();
    });
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
    final sessionService = context.watch<SessionService>();
    final user = auth.currentUser!;
    final recent = sessionService.sessions.take(3).toList();

    return Scaffold(
      appBar: AppBar(title: const Text('Dashboard')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Hello, ${user.fullName}',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              'Dominant hand: ${user.dominantHand}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                _StatCard(
                  label: 'Sessions',
                  value: '${sessionService.sessions.length}',
                ),
                const SizedBox(width: 16),
                _StatCard(
                  label: 'Movements',
                  value: '${MovementCatalog.automatedMovements.length}',
                ),
              ],
            ),
            const SizedBox(height: 32),
            Text('Quick actions', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                _ActionChip(
                  icon: Icons.play_circle_outline,
                  label: 'Start Practice',
                  onTap: () => context.go('/movements'),
                ),
                _ActionChip(
                  icon: Icons.menu_book_outlined,
                  label: 'Tutorials',
                  onTap: () => context.go('/tutorials'),
                ),
                _ActionChip(
                  icon: Icons.videocam_outlined,
                  label: 'Camera Test',
                  onTap: () => context.go('/camera-test'),
                ),
              ],
            ),
            const SizedBox(height: 32),
            Text('Recent sessions', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            if (sessionService.loading)
              const Center(child: CircularProgressIndicator())
            else if (recent.isEmpty)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Text(
                    'No sessions yet. Start your first practice!',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ),
              )
            else
              ...recent.map((s) {
                final movement = MovementCatalog.findById(s.movementId);
                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    title: Text(movement?.name ?? s.movementId),
                    subtitle: Text('${s.durationSeconds}s · ${s.resultStatus}'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context.go('/session-summary/${s.id}'),
                  ),
                );
              }),
          ],
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(value, style: Theme.of(context).textTheme.headlineMedium),
              Text(label, style: Theme.of(context).textTheme.bodySmall),
            ],
          ),
        ),
      ),
    );
  }
}

class _ActionChip extends StatelessWidget {
  const _ActionChip({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ActionChip(
      avatar: Icon(icon, size: 18, color: AppColors.primary),
      label: Text(label),
      backgroundColor: AppColors.card,
      onPressed: onTap,
    );
  }
}
