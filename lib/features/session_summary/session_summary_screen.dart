import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/constants/movement_catalog.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/primary_button.dart';
import '../../core/widgets/status_chip.dart';
import '../../data/models/practice_session.dart';
import '../../data/models/session_check.dart';
import '../../services/session_service.dart';

class SessionSummaryScreen extends StatefulWidget {
  const SessionSummaryScreen({super.key, required this.sessionId});

  final int sessionId;

  @override
  State<SessionSummaryScreen> createState() => _SessionSummaryScreenState();
}

class _SessionSummaryScreenState extends State<SessionSummaryScreen> {
  PracticeSession? _session;
  List<SessionCheck> _checks = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final service = context.read<SessionService>();
    final session = await service.getSession(widget.sessionId);
    final checks = session != null
        ? await service.getChecks(widget.sessionId)
        : <SessionCheck>[];

    if (mounted) {
      setState(() {
        _session = session;
        _checks = checks;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (_session == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Session Summary')),
        body: const Center(child: Text('Session not found')),
      );
    }

    final movement = MovementCatalog.findById(_session!.movementId);
    final dateFormat = DateFormat('MMM d, yyyy · h:mm a');

    return Scaffold(
      appBar: AppBar(
        title: const Text('Session Summary'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/history'),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              movement?.name ?? _session!.movementId,
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              dateFormat.format(_session!.createdAt),
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                StatusChip(status: _session!.resultStatus),
                const SizedBox(width: 12),
                Text('${_session!.durationSeconds}s'),
              ],
            ),
            const SizedBox(height: 24),
            _SummaryRow(
              label: 'Passed',
              value: '${_session!.passedCheckCount}',
              color: AppColors.success,
            ),
            _SummaryRow(
              label: 'Failed',
              value: '${_session!.failedCheckCount}',
              color: AppColors.error,
            ),
            _SummaryRow(
              label: 'Not assessed',
              value: '${_session!.notAssessedCount}',
              color: AppColors.textSecondary,
            ),
            const SizedBox(height: 24),
            Text('Checkpoints', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            if (_checks.isEmpty)
              Text(
                'No checkpoint details saved.',
                style: Theme.of(context).textTheme.bodySmall,
              )
            else
              ..._checks.map(
                (c) {
                  final detailParts = <String>[
                    if (c.message != null && c.message!.isNotEmpty) c.message!,
                    if (c.measuredValue != null && c.measuredValue!.isNotEmpty)
                      'Measured: ${c.measuredValue}',
                    if (c.expectedRange != null && c.expectedRange!.isNotEmpty)
                      'Expected: ${c.expectedRange}',
                  ];
                  return Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: ListTile(
                      title: Text(c.checkpointLabel),
                      subtitle: Text(
                        detailParts.isEmpty
                            ? c.checkpointKey
                            : detailParts.join('\n'),
                      ),
                      isThreeLine: detailParts.length > 1,
                      trailing: StatusChip(status: c.resultStatus),
                    ),
                  );
                },
              ),
            const SizedBox(height: 32),
            PrimaryButton(
              label: 'Back to History',
              onPressed: () => context.go('/history'),
            ),
          ],
        ),
      ),
    );
  }
}

class _SummaryRow extends StatelessWidget {
  const _SummaryRow({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: 12),
          Text(label),
          const Spacer(),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}
