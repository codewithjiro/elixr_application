import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/constants/movement_catalog.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/empty_state.dart';
import '../../services/session_service.dart';

class ProgressScreen extends StatefulWidget {
  const ProgressScreen({super.key});

  @override
  State<ProgressScreen> createState() => _ProgressScreenState();
}

class _ProgressScreenState extends State<ProgressScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<SessionService>().loadSessions();
    });
  }

  @override
  Widget build(BuildContext context) {
    final service = context.watch<SessionService>();
    final sessions = service.sessions;
    final movementStats = service.movementStats;
    final commonFailed = service.commonFailedCheckpoints;

    if (service.loading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Progress')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (sessions.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: const Text('Progress')),
        body: const EmptyState(
          icon: Icons.trending_up,
          title: 'No progress data yet',
          subtitle: 'Complete practice sessions to track your progress.',
        ),
      );
    }

    final passed = sessions.fold<int>(0, (sum, s) => sum + s.passedCheckCount);
    final failed = sessions.fold<int>(0, (sum, s) => sum + s.failedCheckCount);
    final completed = sessions
        .where((s) => s.resultStatus == 'passed' || s.resultStatus == 'partial')
        .length;
    final totalDuration =
        sessions.fold<int>(0, (sum, s) => sum + s.durationSeconds);
    final chartMax = (passed + failed).toDouble();

    return Scaffold(
      appBar: AppBar(title: const Text('Progress')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Based on saved sessions and checkpoint records.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                _Metric(label: 'Sessions', value: '${sessions.length}'),
                const SizedBox(width: 16),
                _Metric(label: 'Completed', value: '$completed'),
                const SizedBox(width: 16),
                _Metric(
                  label: 'Total time',
                  value: '${totalDuration ~/ 60}m ${totalDuration % 60}s',
                ),
              ],
            ),
            const SizedBox(height: 32),
            Text(
              'Checkpoint totals',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 200,
              child: BarChart(
                BarChartData(
                  alignment: BarChartAlignment.spaceAround,
                  maxY: chartMax <= 0 ? 2 : chartMax + 1,
                  barTouchData: BarTouchData(enabled: false),
                  titlesData: FlTitlesData(
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        getTitlesWidget: (value, meta) {
                          switch (value.toInt()) {
                            case 0:
                              return const Text('Passed',
                                  style: TextStyle(fontSize: 12));
                            case 1:
                              return const Text('Failed',
                                  style: TextStyle(fontSize: 12));
                          }
                          return const Text('');
                        },
                      ),
                    ),
                    leftTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: true, reservedSize: 32),
                    ),
                    topTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                    rightTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                  ),
                  gridData: const FlGridData(show: false),
                  borderData: FlBorderData(show: false),
                  barGroups: [
                    BarChartGroupData(
                      x: 0,
                      barRods: [
                        BarChartRodData(
                          toY: passed.toDouble(),
                          color: AppColors.success,
                          width: 40,
                          borderRadius: const BorderRadius.vertical(
                            top: Radius.circular(4),
                          ),
                        ),
                      ],
                    ),
                    BarChartGroupData(
                      x: 1,
                      barRods: [
                        BarChartRodData(
                          toY: failed.toDouble(),
                          color: AppColors.error,
                          width: 40,
                          borderRadius: const BorderRadius.vertical(
                            top: Radius.circular(4),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 32),
            Text(
              'Per-movement sessions',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            ...movementStats.map((stat) {
              final name =
                  MovementCatalog.findById(stat.movementId)?.name ??
                      stat.movementId;
              return Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  title: Text(name),
                  subtitle: Text(
                    '${stat.sessionCount} sessions · '
                    '${stat.passedSessions} passed · '
                    '${stat.partialSessions} partial · '
                    '${stat.failedSessions} failed',
                  ),
                  trailing: Text(
                    '${stat.passedChecks}P / ${stat.failedChecks}F',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ),
              );
            }),
            const SizedBox(height: 24),
            Text(
              'Common failed checkpoints',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            if (commonFailed.isEmpty)
              Text(
                'No failed checkpoints recorded yet.',
                style: Theme.of(context).textTheme.bodySmall,
              )
            else
              ...commonFailed.map(
                (f) => Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    title: Text(f.checkpointLabel),
                    subtitle: Text(f.checkpointKey),
                    trailing: Text(
                      '${f.failCount}×',
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        color: AppColors.error,
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(value, style: Theme.of(context).textTheme.titleLarge),
              Text(label, style: Theme.of(context).textTheme.bodySmall),
            ],
          ),
        ),
      ),
    );
  }
}
