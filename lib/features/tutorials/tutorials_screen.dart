import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/constants/movement_catalog.dart';
import '../../core/theme/app_theme.dart';

class TutorialsScreen extends StatelessWidget {
  const TutorialsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Tutorials')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Text(
            'Automated assessments',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          ...MovementCatalog.automatedMovements.map(
            (m) => _TutorialTile(movementId: m.id, name: m.name, risk: m.risk),
          ),
          const SizedBox(height: 24),
          Text(
            'Tutorial only',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 4),
          Text(
            MovementCatalog.tutorialOnlyLabel,
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 8),
          ...MovementCatalog.tutorialOnlyMovements.map(
            (m) => _TutorialTile(
              movementId: m.id,
              name: m.name,
              risk: m.risk,
              tutorialOnly: true,
            ),
          ),
        ],
      ),
    );
  }
}

class _TutorialTile extends StatelessWidget {
  const _TutorialTile({
    required this.movementId,
    required this.name,
    required this.risk,
    this.tutorialOnly = false,
  });

  final String movementId;
  final String name;
  final String risk;
  final bool tutorialOnly;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        title: Text(name),
        subtitle: Text(
          tutorialOnly ? MovementCatalog.tutorialOnlyLabel : 'Risk: $risk',
          style: Theme.of(context).textTheme.bodySmall,
        ),
        trailing: tutorialOnly
            ? Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.textSecondary.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text('Tutorial', style: TextStyle(fontSize: 11)),
              )
            : const Icon(Icons.chevron_right),
        onTap: () => context.go('/tutorials/$movementId'),
      ),
    );
  }
}
