class User {
  const User({
    required this.id,
    required this.fullName,
    required this.username,
    required this.passwordHash,
    required this.passwordSalt,
    required this.dominantHand,
    required this.onboardingComplete,
    required this.createdAt,
  });

  final int id;
  final String fullName;
  final String username;
  final String passwordHash;
  final String passwordSalt;
  final String dominantHand;
  final bool onboardingComplete;
  final DateTime createdAt;

  factory User.fromMap(Map<String, dynamic> map) {
    return User(
      id: map['id'] as int,
      fullName: map['full_name'] as String,
      username: map['username'] as String,
      passwordHash: map['password_hash'] as String,
      passwordSalt: map['password_salt'] as String,
      dominantHand: map['dominant_hand'] as String,
      onboardingComplete: (map['onboarding_complete'] as int) == 1,
      createdAt: DateTime.parse(map['created_at'] as String),
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'full_name': fullName,
      'username': username,
      'password_hash': passwordHash,
      'password_salt': passwordSalt,
      'dominant_hand': dominantHand,
      'onboarding_complete': onboardingComplete ? 1 : 0,
      'created_at': createdAt.toIso8601String(),
    };
  }

  User copyWith({
    int? id,
    String? fullName,
    String? username,
    String? passwordHash,
    String? passwordSalt,
    String? dominantHand,
    bool? onboardingComplete,
    DateTime? createdAt,
  }) {
    return User(
      id: id ?? this.id,
      fullName: fullName ?? this.fullName,
      username: username ?? this.username,
      passwordHash: passwordHash ?? this.passwordHash,
      passwordSalt: passwordSalt ?? this.passwordSalt,
      dominantHand: dominantHand ?? this.dominantHand,
      onboardingComplete: onboardingComplete ?? this.onboardingComplete,
      createdAt: createdAt ?? this.createdAt,
    );
  }
}
