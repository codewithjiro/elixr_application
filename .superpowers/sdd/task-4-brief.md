### Task 4: Soft safety + practice/camera UI polish

**Files:**
- Create: `lib/features/practice/practice_safety.dart`
- Modify: `lib/features/practice/practice_shell_screen.dart`
- Modify: `lib/features/camera_test/camera_test_screen.dart`
- Modify: `lib/core/widgets/status_chip.dart`
- Modify: `lib/features/onboarding/onboarding_screen.dart`
- Modify: `lib/features/safety/safety_screen.dart`

**Interfaces:**
- Consumes: `resolveStatusBanner`, session flag `PracticeSafetyGate`
- Produces: soft sheet before Start; animated banners/chips; updated copy

- [ ] **Step 1: Implement `PracticeSafetyGate`.**session-only**

```dart
class PracticeSafetyGate {
  static bool _suppressedThisLaunch = false;
  static bool get suppressedThisLaunch => _suppressedThisLaunch;
  static void suppressForLaunch() => _suppressedThisLaunch = true;

  static Future<void> showIfNeeded(BuildContext context) async {
    if (_suppressedThisLaunch) return;
    // showModalBottomSheet — Continue, Don't show again this launch, dismissible
  }
}
```

Wire into `_start()` **before** connecting: `await PracticeSafetyGate.showIfNeeded(context);` then proceed (even if dismissed).

- [ ] **Step 2: Practice shell banners**

Replace ad-hoc warning container with `AnimatedSwitcher` driven by `resolveStatusBanner` + existing local/WS errors. Actionable copy. While `unable_to_assess`, do not run any success animation on chips.

Label offline fallback banner as **demo fallback (not live CV)** if `_useOfflineMock` remains — do not expand onboarding claims.

Add `Semantics` on Start/Stop.

- [ ] **Step 3: StatusChip animation**

Wrap label/`Container` in `AnimatedSwitcher(duration: 200ms, child: ... key: ValueKey(status))`.

- [ ] **Step 4: Camera test + onboarding + safety copy**

- Camera test: remove “mock until Phase 3”; say live readiness checks when backend connected.
- Onboarding: live camera-based checkpoint feedback when backend is running; local storage for history; no “Phase 1 only” claim.
- Safety screen: align bullets with §20 (opaque plastic, no glass, one user, clearance, etc.).

- [ ] **Step 5: Manual smoke**

Run app against backend: open practice → soft sheet → Start → cover lens → low-confidence banner after debounce → uncover → recovery without full reset of prior passes.

- [ ] **Step 6: Commit (if git available)**

```bash
git add lib/features/practice lib/features/camera_test lib/features/onboarding lib/features/safety lib/core/widgets/status_chip.dart
git commit -m "feat(phase5): soft safety reminder and practice status UI polish"
```

---
