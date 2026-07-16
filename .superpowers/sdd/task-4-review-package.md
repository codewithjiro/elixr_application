# Task 4 Review Package
## FILE: lib\features\practice\practice_safety.dart
```
import 'package:flutter/material.dart';

class PracticeSafetyGate {
  const PracticeSafetyGate._();

  static bool _suppressedThisLaunch = false;

  static bool get suppressedThisLaunch => _suppressedThisLaunch;

  static void suppressForLaunch() => _suppressedThisLaunch = true;

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

```
## FILE: lib\features\practice\practice_shell_screen.dart
```
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/constants/app_constants.dart';
import '../../core/constants/movement_catalog.dart';
import '../../core/constants/status_reasons.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/primary_button.dart';
import '../../core/widgets/status_chip.dart';
import '../../data/models/session_check.dart';
import '../../services/auth_service.dart';
import '../../services/practice_service.dart';
import '../../services/session_service.dart';
import '../../services/websocket_service.dart';
import 'practice_safety.dart';

class PracticeShellScreen extends StatefulWidget {
  const PracticeShellScreen({super.key, required this.movementId});

  final String movementId;

  @override
  State<PracticeShellScreen> createState() => _PracticeShellScreenState();
}

class _PracticeShellScreenState extends State<PracticeShellScreen> {
  Timer? _timer;
  int _elapsed = 0;
  bool _running = false;
  bool _busy = false;
  String? _localError;
  bool _useOfflineMock = false;
  WebSocketService? _ws;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _ws ??= context.read<WebSocketService>();
  }

  @override
  void dispose() {
    _timer?.cancel();
    final ws = _ws;
    if (ws != null && ws.isConnected) {
      ws.cancelSession();
      unawaited(ws.disconnect());
    }
    super.dispose();
  }

  Future<void> _start() async {
    await PracticeSafetyGate.showIfNeeded(context);
    if (!mounted) return;

    setState(() {
      _busy = true;
      _localError = null;
      _useOfflineMock = false;
      _elapsed = 0;
    });

    final ws = context.read<WebSocketService>();
    final auth = context.read<AuthService>();
    final healthy = await ws.checkHealth();
    if (!mounted) return;

    if (!healthy) {
      setState(() {
        _useOfflineMock = true;
        _running = true;
        _busy = false;
        _localError = 'Demo fallback — checkpoints are simulated, not live CV.';
      });
      _timer = Timer.periodic(const Duration(seconds: 1), (_) {
        setState(() => _elapsed++);
      });
      return;
    }

    await ws.connect();
    if (!mounted) return;

    if (!ws.isConnected) {
      setState(() {
        _busy = false;
        _localError = ws.errorMessage ?? 'Could not connect to backend.';
      });
      return;
    }

    ws.startSession(
      movementId: widget.movementId,
      dominantHand:
          auth.currentUser?.dominantHand ?? AppConstants.dominantHandRight,
    );

    setState(() {
      _running = true;
      _busy = false;
    });
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      setState(() => _elapsed++);
    });
  }

  Future<void> _stop() async {
    _timer?.cancel();
    setState(() {
      _running = false;
      _busy = true;
    });

    final sessionService = context.read<SessionService>();
    final ws = context.read<WebSocketService>();

    if (_useOfflineMock) {
      final session = await sessionService.saveMockSession(
        movementId: widget.movementId,
        durationSeconds: _elapsed,
      );
      if (mounted) {
        setState(() => _busy = false);
        context.go('/session-summary/${session.id}');
      }
      return;
    }

    final summary = await ws.stopSession();
    await ws.disconnect();

    if (!mounted) return;

    if (summary == null) {
      setState(() {
        _busy = false;
        _localError = 'No session summary received from backend.';
      });
      return;
    }

    final checks = summary.checks
        .map(
          (c) => SessionCheck(
            id: 0,
            sessionId: 0,
            checkpointKey: c.key,
            checkpointLabel: c.label,
            resultStatus: c.uiStatus,
            measuredValue: c.measuredValue,
            expectedRange: c.expectedRange,
            message: c.message,
            createdAt: DateTime.now(),
          ),
        )
        .toList();

    final session = await sessionService.saveBackendSession(
      movementId: summary.movementId.isEmpty
          ? widget.movementId
          : summary.movementId,
      resultStatus: summary.resultStatus,
      durationSeconds: summary.durationSeconds > 0
          ? summary.durationSeconds
          : _elapsed,
      attemptCount: summary.attemptCount,
      passedCheckCount: summary.passedCheckCount,
      failedCheckCount: summary.failedCheckCount,
      notAssessedCount: summary.notAssessedCount,
      detectionInterruptions: summary.detectionInterruptions,
      assessmentVersion: summary.assessmentVersion,
      checks: checks,
    );

    if (mounted) {
      setState(() => _busy = false);
      context.go('/session-summary/${session.id}');
    }
  }

  String _formatTime(int seconds) {
    final m = seconds ~/ 60;
    final s = seconds % 60;
    return '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final movement = MovementCatalog.findById(widget.movementId);
    final ws = context.watch<WebSocketService>();
    final frame = ws.latestFrame;
    final resolvedBanner = resolveStatusBanner(
      assessmentState: frame?.assessmentState,
      statusReason: frame?.statusReason,
      statusMessage: frame?.statusMessage,
      clientStatusReason: ws.clientStatusReason,
    );
    final banner = _useOfflineMock
        ? const StatusBannerInfo(
            message: 'Demo fallback — checkpoints are simulated, not live CV.',
            tone: StatusBannerTone.warning,
          )
        : _localError != null
        ? StatusBannerInfo(message: _localError!, tone: StatusBannerTone.error)
        : resolvedBanner ??
              (ws.errorMessage != null
                  ? StatusBannerInfo(
                      message: ws.errorMessage!,
                      tone: StatusBannerTone.error,
                    )
                  : ws.sessionMessage != null
                  ? StatusBannerInfo(
                      message: ws.sessionMessage!,
                      tone: StatusBannerTone.warning,
                    )
                  : null);
    final assessmentPaused = frame?.assessmentState == 'unable_to_assess';

    final offlineCheckpoints = context
        .read<PracticeService>()
        .getMockCheckpoints(widget.movementId);

    return Scaffold(
      appBar: AppBar(
        title: Text(movement?.name ?? 'Practice'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: _busy
              ? null
              : () async {
                  if (_running && !_useOfflineMock) {
                    await ws.cancelSession();
                    await ws.disconnect();
                  }
                  if (context.mounted) context.go('/movements');
                },
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 200),
              child: banner == null
                  ? const SizedBox.shrink(key: ValueKey('no-banner'))
                  : _PracticeBanner(
                      key: ValueKey('${banner.tone}:${banner.message}'),
                      info: banner,
                    ),
            ),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  flex: 3,
                  child: Column(
                    children: [
                      Text(
                        _formatTime(_elapsed),
                        style: Theme.of(context).textTheme.displayMedium
                            ?.copyWith(
                              color: AppColors.primary,
                              fontFeatures: const [
                                FontFeature.tabularFigures(),
                              ],
                            ),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 12),
                      AspectRatio(
                        aspectRatio: 4 / 3,
                        child: Container(
                          decoration: BoxDecoration(
                            color: AppColors.card,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: AppColors.textSecondary.withValues(
                                alpha: 0.2,
                              ),
                            ),
                          ),
                          clipBehavior: Clip.antiAlias,
                          child: !_useOfflineMock && frame?.frameBytes != null
                              ? Image.memory(
                                  frame!.frameBytes!,
                                  fit: BoxFit.contain,
                                  gaplessPlayback: true,
                                )
                              : Center(
                                  child: Text(
                                    _running
                                        ? (_useOfflineMock
                                              ? 'Offline practice (no frames)'
                                              : 'Waiting for frames…')
                                        : 'Press Start to connect',
                                    style: Theme.of(
                                      context,
                                    ).textTheme.bodySmall,
                                  ),
                                ),
                        ),
                      ),
                      if (frame != null && !_useOfflineMock) ...[
                        const SizedBox(height: 8),
                        Text(
                          '${frame.assessmentState} · ${frame.currentStep}'
                          ' · conf ${frame.trackingConfidence.toStringAsFixed(2)}',
                          style: Theme.of(context).textTheme.bodySmall,
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(width: 24),
                Expanded(
                  flex: 2,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        'Checkpoints',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      Expanded(
                        child: ListView(
                          children: _useOfflineMock
                              ? offlineCheckpoints
                                    .map(
                                      (cp) => _CheckpointCard(
                                        label: cp.label,
                                        status: cp.status,
                                        message: cp.message,
                                        badge: 'MOCK',
                                        animateStatus: true,
                                      ),
                                    )
                                    .toList()
                              : (frame?.checks ?? const [])
                                    .map(
                                      (cp) => _CheckpointCard(
                                        label: cp.label,
                                        status: cp.uiStatus,
                                        message: cp.message,
                                        badge: 'LIVE',
                                        animateStatus: !assessmentPaused,
                                      ),
                                    )
                                    .toList(),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (!_running)
              Semantics(
                button: true,
                enabled: !_busy,
                label: _busy
                    ? 'Connecting practice session'
                    : 'Start practice session',
                excludeSemantics: true,
                child: PrimaryButton(
                  label: _busy ? 'Connecting…' : 'Start Session',
                  onPressed: _busy ? null : _start,
                ),
              )
            else
              Semantics(
                button: true,
                enabled: !_busy,
                label: _busy
                    ? 'Saving practice session'
                    : 'Stop practice session',
                excludeSemantics: true,
                child: PrimaryButton(
                  label: _busy ? 'Saving…' : 'Stop Session',
                  onPressed: _busy ? null : _stop,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _PracticeBanner extends StatelessWidget {
  const _PracticeBanner({super.key, required this.info});

  final StatusBannerInfo info;

  Color get _color => switch (info.tone) {
    StatusBannerTone.success => AppColors.success,
    StatusBannerTone.warning => AppColors.warning,
    StatusBannerTone.error => AppColors.error,
  };

  IconData get _icon => switch (info.tone) {
    StatusBannerTone.success => Icons.check_circle_outline,
    StatusBannerTone.warning => Icons.warning_amber_outlined,
    StatusBannerTone.error => Icons.error_outline,
  };

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      child: Container(
        padding: const EdgeInsets.all(12),
        margin: const EdgeInsets.only(bottom: 16),
        decoration: BoxDecoration(
          color: _color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: _color.withValues(alpha: 0.4)),
        ),
        child: Row(
          children: [
            Icon(_icon, color: _color, size: 20),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                info.message,
                style: TextStyle(color: _color, fontSize: 13),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CheckpointCard extends StatelessWidget {
  const _CheckpointCard({
    required this.label,
    required this.status,
    required this.message,
    required this.badge,
    required this.animateStatus,
  });

  final String label;
  final String status;
  final String message;
  final String badge;
  final bool animateStatus;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    label,
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                ),
                StatusChip(status: status, animate: animateStatus),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 6,
                    vertical: 2,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.secondary.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    badge,
                    style: const TextStyle(
                      fontSize: 10,
                      color: AppColors.secondary,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(message, style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      ),
    );
  }
}

```
## FILE: lib\features\camera_test\camera_test_screen.dart
```
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/constants/app_constants.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/primary_button.dart';
import '../../core/widgets/status_chip.dart';
import '../../services/auth_service.dart';
import '../../services/websocket_service.dart';

class CameraTestScreen extends StatefulWidget {
  const CameraTestScreen({super.key});

  @override
  State<CameraTestScreen> createState() => _CameraTestScreenState();
}

class _CameraTestScreenState extends State<CameraTestScreen> {
  bool _busy = false;
  bool? _healthOk;
  WebSocketService? _ws;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _ws ??= context.read<WebSocketService>();
  }

  Future<void> _probeHealth() async {
    setState(() => _busy = true);
    final ok = await context.read<WebSocketService>().checkHealth();
    if (mounted) {
      setState(() {
        _healthOk = ok;
        _busy = false;
      });
    }
  }

  Future<void> _connectAndPreview() async {
    setState(() => _busy = true);
    final ws = context.read<WebSocketService>();
    final auth = context.read<AuthService>();

    await ws.connect();
    if (!mounted) return;

    if (ws.isConnected) {
      ws.startSession(
        movementId: 'camera_test',
        dominantHand:
            auth.currentUser?.dominantHand ?? AppConstants.dominantHandRight,
      );
    }

    setState(() => _busy = false);
  }

  Future<void> _disconnect() async {
    setState(() => _busy = true);
    final ws = context.read<WebSocketService>();
    await ws.stopSession();
    await ws.disconnect();
    if (mounted) setState(() => _busy = false);
  }

  @override
  void dispose() {
    final ws = _ws;
    if (ws != null && ws.isConnected) {
      ws.cancelSession();
      unawaited(ws.disconnect());
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ws = context.watch<WebSocketService>();
    final frame = ws.latestFrame;

    return Scaffold(
      appBar: AppBar(title: const Text('Camera Test')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              flex: 3,
              child: Container(
                decoration: BoxDecoration(
                  color: AppColors.card,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: AppColors.textSecondary.withValues(alpha: 0.2),
                  ),
                ),
                clipBehavior: Clip.antiAlias,
                child: frame?.frameBytes != null
                    ? Image.memory(
                        frame!.frameBytes!,
                        fit: BoxFit.contain,
                        gaplessPlayback: true,
                      )
                    : Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.videocam_outlined,
                              size: 56,
                              color: AppColors.textSecondary.withValues(
                                alpha: 0.6,
                              ),
                            ),
                            const SizedBox(height: 12),
                            Text(
                              ws.isConnected
                                  ? 'Waiting for frames…'
                                  : 'Not connected',
                              style: Theme.of(context).textTheme.bodyMedium,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              ws.endpointUrl,
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ],
                        ),
                      ),
              ),
            ),
            const SizedBox(width: 24),
            Expanded(
              flex: 2,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Backend connection',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 12),
                  _InfoRow(
                    label: 'WebSocket',
                    child: StatusChip(
                      status: switch (ws.connectionState) {
                        WsConnectionState.connected =>
                          AppConstants.resultPassed,
                        WsConnectionState.connecting =>
                          AppConstants.resultInProgress,
                        WsConnectionState.error => AppConstants.resultFailed,
                        WsConnectionState.disconnected =>
                          AppConstants.resultNotAssessed,
                      },
                    ),
                  ),
                  if (_healthOk != null) ...[
                    const SizedBox(height: 8),
                    _InfoRow(
                      label: '/health',
                      child: Text(
                        _healthOk! ? 'ok' : 'unreachable',
                        style: TextStyle(
                          color: _healthOk!
                              ? AppColors.success
                              : AppColors.error,
                        ),
                      ),
                    ),
                  ],
                  if (frame != null) ...[
                    const SizedBox(height: 8),
                    _InfoRow(
                      label: 'State',
                      child: Text(frame.assessmentState),
                    ),
                    _InfoRow(
                      label: 'Body',
                      child: Text(frame.bodyDetected ? 'yes' : 'no'),
                    ),
                    _InfoRow(
                      label: 'Bottle',
                      child: Text(frame.bottleDetected ? 'yes' : 'no'),
                    ),
                    _InfoRow(
                      label: 'Source',
                      child: Text(frame.cameraSource ?? '—'),
                    ),
                    _InfoRow(
                      label: 'Confidence',
                      child: Text(frame.trackingConfidence.toStringAsFixed(2)),
                    ),
                  ],
                  if (ws.errorMessage != null) ...[
                    const SizedBox(height: 12),
                    Text(
                      ws.errorMessage!,
                      style: const TextStyle(
                        color: AppColors.error,
                        fontSize: 13,
                      ),
                    ),
                  ],
                  const Spacer(),
                  PrimaryButton(
                    label: 'Check /health',
                    onPressed: _busy ? null : _probeHealth,
                  ),
                  const SizedBox(height: 12),
                  if (!ws.isConnected)
                    PrimaryButton(
                      label: 'Connect & preview',
                      onPressed: _busy ? null : _connectAndPreview,
                    )
                  else
                    PrimaryButton(
                      label: 'Disconnect',
                      onPressed: _busy ? null : _disconnect,
                    ),
                  const SizedBox(height: 12),
                  Text(
                    'Shows live camera and assessment readiness when the '
                    'backend is running.',
                    style: Theme.of(context).textTheme.bodySmall,
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.child});

  final String label;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 100,
            child: Text(label, style: Theme.of(context).textTheme.bodySmall),
          ),
          Expanded(child: child),
        ],
      ),
    );
  }
}

```
## FILE: lib\core\widgets\status_chip.dart
```
import 'package:flutter/material.dart';

import '../constants/app_constants.dart';
import '../theme/app_theme.dart';

class StatusChip extends StatelessWidget {
  const StatusChip({super.key, required this.status, this.animate = true});

  final String status;
  final bool animate;

  Color get _color {
    switch (status) {
      case AppConstants.resultPassed:
        return AppColors.success;
      case AppConstants.resultFailed:
        return AppColors.error;
      case AppConstants.resultPartial:
        return AppColors.warning;
      case AppConstants.resultNotAssessed:
        return AppColors.textSecondary;
      case AppConstants.resultInProgress:
        return AppColors.secondary;
      default:
        return AppColors.textSecondary;
    }
  }

  String get _label {
    switch (status) {
      case AppConstants.resultPassed:
        return 'Passed';
      case AppConstants.resultFailed:
        return 'Failed';
      case AppConstants.resultPartial:
        return 'Partial';
      case AppConstants.resultNotAssessed:
        return 'Not assessed';
      case AppConstants.resultInProgress:
        return 'In progress';
      default:
        return status;
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedSwitcher(
      duration: animate ? const Duration(milliseconds: 200) : Duration.zero,
      child: Container(
        key: ValueKey(status),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: _color.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: _color.withValues(alpha: 0.5)),
        ),
        child: Text(
          _label,
          style: TextStyle(
            color: _color,
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }
}

```
## FILE: lib\features\onboarding\onboarding_screen.dart
```
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
                  value: (_step + 1) / 3,
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
                    if (_step < 2)
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

```
## FILE: lib\features\safety\safety_screen.dart
```
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

```

