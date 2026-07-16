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
                    'backend is running. For reliable tracking: one user, '
                    'front-facing stable camera, full body visible, good '
                    'lighting, clear area, and an opaque plastic practice '
                    'bottle (no glass).',
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
