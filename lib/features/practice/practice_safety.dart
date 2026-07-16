import 'package:flutter/material.dart';

class PracticeSafetyGate {
  const PracticeSafetyGate._();

  static bool _suppressedThisLaunch = false;

  static bool get suppressedThisLaunch => _suppressedThisLaunch;

  static void suppressForLaunch() => _suppressedThisLaunch = true;

  @visibleForTesting
  static void resetForTests() => _suppressedThisLaunch = false;

  static Future<void> showIfNeeded(BuildContext context) async {
    if (_suppressedThisLaunch) return;

    await showModalBottomSheet<void>(
      context: context,
      isDismissible: true,
      enableDrag: true,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (sheetContext) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Practice safely',
                style: Theme.of(sheetContext).textTheme.titleLarge,
              ),
              const SizedBox(height: 12),
              const Text(
                'Use one user and one opaque plastic practice bottle—never '
                'glass. Face a stable, front-facing camera with your full body '
                'visible, good lighting, and a clear practice area. Avoid '
                'advanced tosses near people or breakable objects, and stop if '
                'you feel pain.',
              ),
              const SizedBox(height: 20),
              FilledButton(
                onPressed: () => Navigator.of(sheetContext).pop(),
                child: const Text('I understand — continue'),
              ),
              const SizedBox(height: 8),
              TextButton(
                onPressed: () {
                  suppressForLaunch();
                  Navigator.of(sheetContext).pop();
                },
                child: const Text('Don’t show again this launch'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
