import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/constants/app_constants.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/primary_button.dart';
import '../../services/auth_service.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  static const _practiceSetupBullets = [
    'One user at a time',
    'Stable, front-facing camera with your full body visible',
    'Sufficient lighting and a clear practice area',
    'Opaque plastic practice bottle only — never glass',
  ];

  int _step = 0;
  String _dominantHand = AppConstants.dominantHandRight;
  bool _loading = false;

  Future<void> _finish() async {
    setState(() => _loading = true);
    await context.read<AuthService>().completeOnboarding(
      dominantHand: _dominantHand,
    );
    if (mounted) context.go('/dashboard');
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
    _dominantHand = auth.currentUser?.dominantHand ?? _dominantHand;

    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                LinearProgressIndicator(
                  value: (_step + 1) / 4,
                  backgroundColor: AppColors.card,
                  color: AppColors.primary,
                ),
                const SizedBox(height: 32),
                if (_step == 0) ...[
                  Text(
                    'Welcome to ELIXR',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'ELIXR helps you practice flair bartending movements with '
                    'live camera-based checkpoint feedback when the backend is '
                    'running. Your session history is stored locally.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ] else if (_step == 1) ...[
                  Text(
                    'Confirm your dominant hand',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 16),
                  SegmentedButton<String>(
                    segments: const [
                      ButtonSegment(
                        value: AppConstants.dominantHandRight,
                        label: Text('Right'),
                      ),
                      ButtonSegment(
                        value: AppConstants.dominantHandLeft,
                        label: Text('Left'),
                      ),
                    ],
                    selected: {_dominantHand},
                    onSelectionChanged: (s) =>
                        setState(() => _dominantHand = s.first),
                  ),
                ] else if (_step == 2) ...[
                  Text(
                    'Practice setup',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'For reliable live assessment:',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 8),
                  ..._practiceSetupBullets.map(
                    (bullet) => Padding(
                      padding: const EdgeInsets.only(bottom: 6),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '• ',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                          Expanded(
                            child: Text(
                              bullet,
                              style: Theme.of(context).textTheme.bodyMedium,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ] else ...[
                  Text(
                    'You\'re all set!',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Explore tutorials, start a practice session, or run a '
                    'camera test. Live assessment is available while the '
                    'backend is connected.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
                const SizedBox(height: 32),
                Row(
                  children: [
                    if (_step > 0)
                      TextButton(
                        onPressed: () => setState(() => _step--),
                        child: const Text('Back'),
                      ),
                    const Spacer(),
                    if (_step < 3)
                      PrimaryButton(
                        label: 'Next',
                        expanded: false,
                        onPressed: () => setState(() => _step++),
                      )
                    else
                      PrimaryButton(
                        label: 'Go to Dashboard',
                        expanded: false,
                        isLoading: _loading,
                        onPressed: _finish,
                      ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
