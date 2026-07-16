import '../../data/models/movement.dart';

class MovementCatalog {
  static const tutorialOnlyLabel =
      'Tutorial only — no automated assessment';

  static const automatedMovements = [
    Movement(
      id: 'ready_stance',
      name: 'Ready Stance',
      risk: 'Low',
      tutorialOnly: false,
      assessmentEnabled: true,
    ),
    Movement(
      id: 'balanced_stance_hold',
      name: 'Balanced Stance Hold',
      risk: 'Low',
      tutorialOnly: false,
      assessmentEnabled: true,
    ),
    Movement(
      id: 'basic_bottle_hold',
      name: 'Basic Bottle Hold Position',
      risk: 'Medium',
      tutorialOnly: false,
      assessmentEnabled: true,
    ),
    Movement(
      id: 'front_bottle_lift',
      name: 'Front Bottle Lift',
      risk: 'Low–Medium',
      tutorialOnly: false,
      assessmentEnabled: true,
    ),
    Movement(
      id: 'side_bottle_lift',
      name: 'Side Bottle Lift',
      risk: 'Low–Medium',
      tutorialOnly: false,
      assessmentEnabled: true,
    ),
    Movement(
      id: 'bent_arm_preparation',
      name: 'Bent-Arm Preparation',
      risk: 'Low',
      tutorialOnly: false,
      assessmentEnabled: true,
    ),
    Movement(
      id: 'arm_extension',
      name: 'Arm Extension',
      risk: 'Low',
      tutorialOnly: false,
      assessmentEnabled: true,
    ),
    Movement(
      id: 'controlled_bottle_lowering',
      name: 'Controlled Bottle Lowering',
      risk: 'Medium',
      tutorialOnly: false,
      assessmentEnabled: true,
    ),
    Movement(
      id: 'hand_to_hand_transfer',
      name: 'Basic Hand-to-Hand Transfer',
      risk: 'Medium–High',
      tutorialOnly: false,
      assessmentEnabled: true,
    ),
    Movement(
      id: 'toss_preparation',
      name: 'Toss Preparation Position',
      risk: 'Low',
      tutorialOnly: false,
      assessmentEnabled: true,
    ),
  ];

  static const tutorialOnlyMovements = [
    Movement(id: 'normal_grip', name: 'Normal Grip', risk: '—', tutorialOnly: true, assessmentEnabled: false),
    Movement(id: 'bartenders_grip', name: "Bartender's Grip", risk: '—', tutorialOnly: true, assessmentEnabled: false),
    Movement(id: 'reverse_grip', name: 'Reverse Grip', risk: '—', tutorialOnly: true, assessmentEnabled: false),
    Movement(id: 'hand_stall', name: 'Hand Stall', risk: '—', tutorialOnly: true, assessmentEnabled: false),
    Movement(id: 'arm_stall', name: 'Arm Stall', risk: '—', tutorialOnly: true, assessmentEnabled: false),
    Movement(id: 'elbow_stall', name: 'Elbow Stall', risk: '—', tutorialOnly: true, assessmentEnabled: false),
    Movement(id: 'clip', name: 'Clip', risk: '—', tutorialOnly: true, assessmentEnabled: false),
    Movement(id: 'tap', name: 'Tap', risk: '—', tutorialOnly: true, assessmentEnabled: false),
    Movement(id: 'basket', name: 'Basket', risk: '—', tutorialOnly: true, assessmentEnabled: false),
    Movement(id: 'switching', name: 'Switching', risk: '—', tutorialOnly: true, assessmentEnabled: false),
    Movement(id: 'front_flip', name: 'Front Flip', risk: '—', tutorialOnly: true, assessmentEnabled: false),
    Movement(id: 'side_flip', name: 'Side Flip', risk: '—', tutorialOnly: true, assessmentEnabled: false),
    Movement(id: 'shadow_pass', name: 'Shadow Pass', risk: '—', tutorialOnly: true, assessmentEnabled: false),
    Movement(id: 'behind_the_back', name: 'Behind the Back', risk: '—', tutorialOnly: true, assessmentEnabled: false),
    Movement(id: 'bump', name: 'Bump', risk: '—', tutorialOnly: true, assessmentEnabled: false),
  ];

  static Movement? findById(String id) {
    for (final m in [...automatedMovements, ...tutorialOnlyMovements]) {
      if (m.id == id) return m;
    }
    return null;
  }

  static List<Movement> get allMovements =>
      [...automatedMovements, ...tutorialOnlyMovements];

  static List<Movement> get practiceMovements =>
      automatedMovements.where((m) => m.assessmentEnabled).toList();
}
