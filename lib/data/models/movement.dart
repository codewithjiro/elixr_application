class Movement {
  const Movement({
    required this.id,
    required this.name,
    required this.risk,
    required this.tutorialOnly,
    this.assessmentEnabled = true,
  });

  final String id;
  final String name;
  final String risk;
  final bool tutorialOnly;

  /// False until rules, tests, and known limitations exist (Phase 3 exit).
  final bool assessmentEnabled;
}
