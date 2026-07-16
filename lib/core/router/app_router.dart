import 'package:go_router/go_router.dart';

import '../../features/auth/login_screen.dart';
import '../../features/auth/register_screen.dart';
import '../../features/camera_test/camera_test_screen.dart';
import '../../features/dashboard/dashboard_screen.dart';
import '../../features/history/history_screen.dart';
import '../../features/movements/movement_selection_screen.dart';
import '../../features/onboarding/onboarding_screen.dart';
import '../../features/practice/practice_shell_screen.dart';
import '../../features/progress/progress_screen.dart';
import '../../features/safety/safety_screen.dart';
import '../../features/session_summary/session_summary_screen.dart';
import '../../features/settings/settings_screen.dart';
import '../../features/shell/main_shell.dart';
import '../../features/tutorials/tutorial_detail_screen.dart';
import '../../features/tutorials/tutorials_screen.dart';
import '../../services/auth_service.dart';

class AppRouter {
  static GoRouter create(AuthService authService) {
    return GoRouter(
      initialLocation: '/login',
      refreshListenable: authService,
      redirect: (context, state) {
        if (!authService.isInitialized) return null;

        final isAuthRoute =
            state.matchedLocation == '/login' ||
            state.matchedLocation == '/register';
        final isOnboarding = state.matchedLocation == '/onboarding';

        if (!authService.isLoggedIn) {
          return isAuthRoute ? null : '/login';
        }

        if (authService.needsOnboarding) {
          return isOnboarding ? null : '/onboarding';
        }

        if (isAuthRoute || isOnboarding) {
          return '/dashboard';
        }

        return null;
      },
      routes: [
        GoRoute(
          path: '/login',
          builder: (context, state) => const LoginScreen(),
        ),
        GoRoute(
          path: '/register',
          builder: (context, state) => const RegisterScreen(),
        ),
        GoRoute(
          path: '/onboarding',
          builder: (context, state) => const OnboardingScreen(),
        ),
        ShellRoute(
          builder: (context, state, child) => MainShell(child: child),
          routes: [
            GoRoute(
              path: '/dashboard',
              builder: (context, state) => const DashboardScreen(),
            ),
            GoRoute(
              path: '/tutorials',
              builder: (context, state) => const TutorialsScreen(),
              routes: [
                GoRoute(
                  path: ':movementId',
                  builder: (context, state) => TutorialDetailScreen(
                    movementId: state.pathParameters['movementId']!,
                  ),
                ),
              ],
            ),
            GoRoute(
              path: '/movements',
              builder: (context, state) => const MovementSelectionScreen(),
            ),
            GoRoute(
              path: '/camera-test',
              builder: (context, state) => const CameraTestScreen(),
            ),
            GoRoute(
              path: '/history',
              builder: (context, state) => const HistoryScreen(),
            ),
            GoRoute(
              path: '/progress',
              builder: (context, state) => const ProgressScreen(),
            ),
            GoRoute(
              path: '/safety',
              builder: (context, state) => const SafetyScreen(),
            ),
            GoRoute(
              path: '/settings',
              builder: (context, state) => const SettingsScreen(),
            ),
          ],
        ),
        GoRoute(
          path: '/practice/:movementId',
          builder: (context, state) => PracticeShellScreen(
            movementId: state.pathParameters['movementId']!,
          ),
        ),
        GoRoute(
          path: '/session-summary/:sessionId',
          builder: (context, state) => SessionSummaryScreen(
            sessionId: int.parse(state.pathParameters['sessionId']!),
          ),
        ),
      ],
    );
  }
}
