import 'package:elixr_application/core/constants/app_constants.dart';
import 'package:elixr_application/core/widgets/status_chip.dart';
import 'package:elixr_application/features/practice/practice_safety.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  setUp(PracticeSafetyGate.resetForTests);
  tearDown(PracticeSafetyGate.resetForTests);

  testWidgets('safety reminder can be suppressed for the current launch', (
    tester,
  ) async {
    late BuildContext hostContext;
    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder: (context) {
            hostContext = context;
            return const SizedBox();
          },
        ),
      ),
    );

    final reminder = PracticeSafetyGate.showIfNeeded(hostContext);
    await tester.pumpAndSettle();

    expect(find.text('Practice safely'), findsOneWidget);
    expect(find.text('I understand — continue'), findsOneWidget);

    await tester.tap(find.text('Don’t show again this launch'));
    await tester.pumpAndSettle();
    await reminder;

    expect(PracticeSafetyGate.suppressedThisLaunch, isTrue);
    await PracticeSafetyGate.showIfNeeded(hostContext);
    expect(find.text('Practice safely'), findsNothing);
  });

  testWidgets('status chip cross-fades when status changes', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: StatusChip(status: AppConstants.resultInProgress),
      ),
    );

    expect(find.byType(AnimatedSwitcher), findsOneWidget);

    await tester.pumpWidget(
      const MaterialApp(home: StatusChip(status: AppConstants.resultPassed)),
    );
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('In progress'), findsOneWidget);
    expect(find.text('Passed'), findsOneWidget);
  });
}
