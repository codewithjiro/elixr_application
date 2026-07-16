import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/constants/movement_catalog.dart';
import '../../core/theme/app_theme.dart';

class MovementSelectionScreen extends StatelessWidget {
  const MovementSelectionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Start Practice')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Text(
            'Select a workshop movement. Only movements with written rules '
            'and tests are practice-enabled (Phase 3 live CV).',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 16),
          ...MovementCatalog.automatedMovements.map((m) {
            final enabled = m.assessmentEnabled;
            return Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: ListTile(
                title: Text(m.name),
                subtitle: Text(
                  enabled
                      ? 'Risk: ${m.risk} · Live assessment'
                      : 'Risk: ${m.risk} · Disabled — incomplete rules/tests',
                ),
                trailing: Icon(
                  enabled ? Icons.play_arrow : Icons.lock_outline,
                  color: enabled ? AppColors.primary : AppColors.textSecondary,
                ),
                enabled: enabled,
                onTap: enabled ? () => context.go('/practice/${m.id}') : null,
              ),
            );
          }),
        ],
      ),
    );
  }
}
