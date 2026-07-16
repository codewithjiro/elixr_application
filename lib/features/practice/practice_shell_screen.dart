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
            Expanded(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Expanded(
                    flex: 3,
                    child: Column(
                      children: [
                        Text(
                          _formatTime(_elapsed),
                          style: Theme.of(context).textTheme.headlineMedium
                              ?.copyWith(
                                color: AppColors.primary,
                                fontFeatures: const [
                                  FontFeature.tabularFigures(),
                                ],
                              ),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 12),
                        Expanded(
                          child: Center(
                            child: AspectRatio(
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
                                child:
                                    !_useOfflineMock &&
                                        frame?.frameBytes != null
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
