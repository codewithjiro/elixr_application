import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

class SafetyScreen extends StatelessWidget {
  const SafetyScreen({super.key});

  static const _guidelines = [
    (
      title: 'Set up the camera',
      body:
          'Practice one user at a time. Face a stable, front-facing camera with '
          'your full body visible, sufficient lighting, and an uncluttered '
          'background.',
    ),
    (
      title: 'Use the right bottle',
      body:
          'Use one clearly visible, opaque plastic practice bottle. Never '
          'practice with a glass bottle.',
    ),
    (
      title: 'Clear your practice area',
      body:
          'Keep people, breakable objects, and other obstacles away from the '
          'full bottle path.',
    ),
    (
      title: 'Keep movements controlled',
      body:
          'Use slow beginner movements. Do not attempt advanced tosses near '
          'people or breakable objects.',
    ),
    (
      title: 'Stop when needed',
      body:
          'Stop immediately if you feel pain or fatigue, or if you lose '
          'control of the bottle.',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Safety Guide')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.error.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppColors.error.withValues(alpha: 0.4)),
            ),
            child: const Row(
              children: [
                Icon(Icons.warning_amber, color: AppColors.error),
                SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Flair bartending involves risk. Always practice responsibly.',
                    style: TextStyle(color: AppColors.error),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          ..._guidelines.map(
            (g) => Card(
              margin: const EdgeInsets.only(bottom: 12),
              child: ListTile(
                leading: const Icon(
                  Icons.check_circle_outline,
                  color: AppColors.success,
                ),
                title: Text(g.title),
                subtitle: Text(g.body),
                isThreeLine: true,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
