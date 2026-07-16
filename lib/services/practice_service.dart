import '../core/constants/app_constants.dart';
import '../core/constants/movement_catalog.dart';

class PracticeService {
  /// Mock checkpoint data for Phase 1 practice shell UI.
  List<MockCheckpoint> getMockCheckpoints(String movementId) {
    final movement = MovementCatalog.findById(movementId);
    return [
      MockCheckpoint(
        key: 'stance_width',
        label: 'Stance Width',
        status: AppConstants.resultPassed,
        message: 'Feet shoulder-width apart',
      ),
      MockCheckpoint(
        key: 'arm_angle',
        label: 'Arm Angle',
        status: AppConstants.resultFailed,
        message: 'Extend arm further',
      ),
      MockCheckpoint(
        key: 'bottle_grip',
        label: 'Bottle Grip',
        status: AppConstants.resultNotAssessed,
        message: 'Awaiting detection (Phase 2)',
      ),
      MockCheckpoint(
        key: 'movement_${movement?.id ?? movementId}',
        label: movement?.name ?? 'Movement Form',
        status: AppConstants.resultPartial,
        message: 'Partial alignment detected',
      ),
    ];
  }
}

class MockCheckpoint {
  const MockCheckpoint({
    required this.key,
    required this.label,
    required this.status,
    required this.message,
  });

  final String key;
  final String label;
  final String status;
  final String message;
}
