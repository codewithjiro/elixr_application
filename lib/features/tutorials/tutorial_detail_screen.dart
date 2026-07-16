import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/constants/movement_catalog.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/primary_button.dart';

class TutorialDetailScreen extends StatelessWidget {
  const TutorialDetailScreen({super.key, required this.movementId});

  final String movementId;

  @override
  Widget build(BuildContext context) {
    final movement = MovementCatalog.findById(movementId);

    if (movement == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Tutorial')),
        body: const Center(child: Text('Movement not found')),
      );
    }

    return Scaffold(
      appBar: AppBar(title: Text(movement.name)),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (movement.tutorialOnly)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                margin: const EdgeInsets.only(bottom: 16),
                decoration: BoxDecoration(
                  color: AppColors.textSecondary.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  MovementCatalog.tutorialOnlyLabel,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
            Text('Overview', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(
              movement.tutorialOnly
                  ? 'Video tutorial content will be added in a future phase. '
                      'This movement has no automated scoring.'
                  : 'Learn the correct form for ${movement.name}. '
                      'Risk level: ${movement.risk}. '
                      'MOCK tutorial steps shown below.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 24),
            Text('Steps (MOCK)', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            const _Step(number: 1, text: 'Set up in ready stance facing the camera'),
            const _Step(number: 2, text: 'Grip the bottle with your dominant hand'),
            const _Step(number: 3, text: 'Execute the movement slowly and with control'),
            const _Step(number: 4, text: 'Return to neutral position'),
            if (!movement.tutorialOnly) ...[
              const SizedBox(height: 32),
              PrimaryButton(
                label: 'Practice this movement',
                onPressed: () => context.go('/practice/$movementId'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _Step extends StatelessWidget {
  const _Step({required this.number, required this.text});

  final int number;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(
            radius: 14,
            backgroundColor: AppColors.primary,
            child: Text('$number', style: const TextStyle(fontSize: 12)),
          ),
          const SizedBox(width: 12),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }
}
