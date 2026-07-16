import 'dart:convert';
import 'dart:math';

import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart';

import '../core/constants/app_constants.dart';
import '../data/models/user.dart';
import '../data/repositories/settings_repository.dart';
import '../data/repositories/user_repository.dart';

class AuthService extends ChangeNotifier {
  AuthService(this._userRepo, this._settingsRepo);

  final UserRepository _userRepo;
  final SettingsRepository _settingsRepo;

  User? _currentUser;
  bool _initialized = false;

  User? get currentUser => _currentUser;
  bool get isLoggedIn => _currentUser != null;
  bool get isInitialized => _initialized;
  bool get needsOnboarding =>
      _currentUser != null && !_currentUser!.onboardingComplete;

  Future<void> init() async {
    final userIdStr = await _settingsRepo.get(AppConstants.settingCurrentUserId);
    if (userIdStr != null) {
      final userId = int.tryParse(userIdStr);
      if (userId != null) {
        _currentUser = await _userRepo.findById(userId);
      }
    }
    _initialized = true;
    notifyListeners();
  }

  Future<String?> register({
    required String fullName,
    required String username,
    required String password,
    required String dominantHand,
  }) async {
    if (fullName.trim().isEmpty ||
        username.trim().isEmpty ||
        password.length < 4) {
      return 'Please fill all fields (password min 4 characters).';
    }

    final existing = await _userRepo.findByUsername(username.trim());
    if (existing != null) {
      return 'Username already taken.';
    }

    final salt = _generateSalt();
    final hash = _hashPassword(password, salt);
    final user = await _userRepo.create(
      fullName: fullName.trim(),
      username: username.trim(),
      passwordHash: hash,
      passwordSalt: salt,
      dominantHand: dominantHand,
    );

    await _setCurrentUser(user);
    return null;
  }

  Future<String?> login({
    required String username,
    required String password,
  }) async {
    final user = await _userRepo.findByUsername(username.trim());
    if (user == null) {
      return 'Invalid username or password.';
    }

    final hash = _hashPassword(password, user.passwordSalt);
    if (hash != user.passwordHash) {
      return 'Invalid username or password.';
    }

    await _setCurrentUser(user);
    return null;
  }

  Future<void> completeOnboarding({required String dominantHand}) async {
    if (_currentUser == null) return;
    await _userRepo.updateDominantHand(_currentUser!.id, dominantHand);
    await _userRepo.updateOnboardingComplete(_currentUser!.id, true);
    _currentUser = await _userRepo.findById(_currentUser!.id);
    notifyListeners();
  }

  Future<void> logout() async {
    _currentUser = null;
    await _settingsRepo.remove(AppConstants.settingCurrentUserId);
    notifyListeners();
  }

  Future<void> _setCurrentUser(User user) async {
    _currentUser = user;
    await _settingsRepo.set(
      AppConstants.settingCurrentUserId,
      user.id.toString(),
    );
    notifyListeners();
  }

  String _generateSalt() {
    final random = Random.secure();
    final bytes = List<int>.generate(16, (_) => random.nextInt(256));
    return base64Encode(bytes);
  }

  String _hashPassword(String password, String salt) {
    final bytes = utf8.encode('$salt$password');
    return sha256.convert(bytes).toString();
  }
}
