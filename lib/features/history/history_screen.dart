import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/constants/app_constants.dart';
import '../../core/constants/movement_catalog.dart';
import '../../core/widgets/empty_state.dart';
import '../../core/widgets/status_chip.dart';
import '../../data/models/practice_session.dart';
import '../../services/session_service.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  String? _movementFilter;
  String? _statusFilter;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<SessionService>().loadSessions();
    });
  }

  List<PracticeSession> _filtered(List<PracticeSession> sessions) {
    return sessions.where((s) {
      if (_movementFilter != null && s.movementId != _movementFilter) {
        return false;
      }
      if (_statusFilter != null && s.resultStatus != _statusFilter) {
        return false;
      }
      return true;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final sessionService = context.watch<SessionService>();
    final dateFormat = DateFormat('MMM d, yyyy · h:mm a');
    final filtered = _filtered(sessionService.sessions);

    return Scaffold(
      appBar: AppBar(title: const Text('History')),
      body: sessionService.loading
          ? const Center(child: CircularProgressIndicator())
          : sessionService.sessions.isEmpty
              ? const EmptyState(
                  icon: Icons.history,
                  title: 'No practice sessions yet',
                  subtitle: 'Complete a practice session to see it here.',
                )
              : Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(24, 16, 24, 8),
                      child: Row(
                        children: [
                          Expanded(
                            child: DropdownButtonFormField<String?>(
                              initialValue: _movementFilter,
                              decoration: const InputDecoration(
                                labelText: 'Movement',
                                isDense: true,
                                border: OutlineInputBorder(),
                              ),
                              items: [
                                const DropdownMenuItem(
                                  value: null,
                                  child: Text('All movements'),
                                ),
                                ...MovementCatalog.practiceMovements.map(
                                  (m) => DropdownMenuItem(
                                    value: m.id,
                                    child: Text(
                                      m.name,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                ),
                              ],
                              onChanged: (value) =>
                                  setState(() => _movementFilter = value),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: DropdownButtonFormField<String?>(
                              initialValue: _statusFilter,
                              decoration: const InputDecoration(
                                labelText: 'Status',
                                isDense: true,
                                border: OutlineInputBorder(),
                              ),
                              items: const [
                                DropdownMenuItem(
                                  value: null,
                                  child: Text('All statuses'),
                                ),
                                DropdownMenuItem(
                                  value: AppConstants.resultPassed,
                                  child: Text('Passed'),
                                ),
                                DropdownMenuItem(
                                  value: AppConstants.resultPartial,
                                  child: Text('Partial'),
                                ),
                                DropdownMenuItem(
                                  value: AppConstants.resultFailed,
                                  child: Text('Failed'),
                                ),
                                DropdownMenuItem(
                                  value: AppConstants.resultNotAssessed,
                                  child: Text('Not assessed'),
                                ),
                              ],
                              onChanged: (value) =>
                                  setState(() => _statusFilter = value),
                            ),
                          ),
                        ],
                      ),
                    ),
                    if (filtered.isEmpty)
                      const Expanded(
                        child: EmptyState(
                          icon: Icons.filter_alt_off,
                          title: 'No matching sessions',
                          subtitle: 'Try a different movement or status filter.',
                        ),
                      )
                    else
                      Expanded(
                        child: ListView.builder(
                          padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
                          itemCount: filtered.length,
                          itemBuilder: (context, index) {
                            final session = filtered[index];
                            final movement =
                                MovementCatalog.findById(session.movementId);

                            return Card(
                              margin: const EdgeInsets.only(bottom: 8),
                              child: ListTile(
                                title:
                                    Text(movement?.name ?? session.movementId),
                                subtitle: Text(
                                  '${dateFormat.format(session.createdAt)} · '
                                  '${session.durationSeconds}s · '
                                  '${session.passedCheckCount}P / '
                                  '${session.failedCheckCount}F',
                                ),
                                trailing:
                                    StatusChip(status: session.resultStatus),
                                onTap: () => context
                                    .go('/session-summary/${session.id}'),
                              ),
                            );
                          },
                        ),
                      ),
                  ],
                ),
    );
  }
}
