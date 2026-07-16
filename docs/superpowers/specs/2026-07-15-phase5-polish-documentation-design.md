# Phase 5 — Polish and Documentation Design

**Date:** 2026-07-15  
**Status:** Approved (design dialogue §§1–4 + post-spec revisions)  
**Approach:** Thin polish pass on existing Flutter ↔ WebSocket ↔ Python stack  
**Non-goals:** Redesign, packaging (`.exe`), cloud, new movements, checkpoint-rule rewrites beyond the low-confidence gate, router rewrite for page transitions

---

## 1. Goals and exit criteria

From `elixr_plan.md` Phase 5, refined by design approval:

1. Improve spacing, accessibility, keyboard behavior, and desktop responsiveness on key screens (practice, camera test, onboarding, safety) without redesigning Phase 0–4 flows.
2. Add restrained animations: banner `AnimatedSwitcher`, `StatusChip` cross-fade; **skip** custom route transitions if they require a router rewrite.
3. Improve camera / backend / model error messages with actionable copy and consistent reason codes.
4. Clear low-confidence state: UI banner + backend threshold with consecutive-frame debounce/recovery; additive `status_reason` / `status_message`.
5. Soft safety reminders before **active practice** only (session-only memory flag).
6. Document a **10-minute demo stability check** (not a formal soak test) with practical pass conditions and tested-environment notes.
7. Replace root `README.md` with reproducible setup + troubleshooting; add `backend/README_PHASE5.md`.
8. In-repo manuscript claims checklist with four claim tiers. No external thesis manuscript edits.

**Exit criteria:** App is stable for demonstration; README is reproducible; manuscript materials in-repo do not claim features that are disabled or unvalidated.

**Language:** Prefer **checkpoint statuses** and **session result metrics** (`passed_check_count`, `failed_check_count`, `not_assessed_count`, `result_status`). Do not describe freezing “scores” or skill percentages.

---

## 2. Architecture (scope boundary)

| Layer | Change |
|---|---|
| Flutter | Soft safety sheet before practice Start; low-confidence / error banners; spacing/focus polish; chip/banner animations; parse optional WS fields; client-side reason codes for disconnect/protocol |
| Backend | Fixed `status_reason` enum (+ `internal_error`); reason priority; optional `status_message`; confidence debounce/recovery; freeze assessor progression while unable; preserve prior `passed` checkpoints |
| Docs | Root README, `README_PHASE5.md`, manuscript claims checklist, demo stability checklist |

`assessment_state` remains the **source of truth** for assessment lifecycle. `status_reason` explains *why*; it must not invent a parallel state machine.

---

## 3. `tracking_confidence` calculation

Document and keep (Phase 5 does not invent a second confidence metric). Computed each frame in `LiveAssessmentSession.next_frame_event` after pose/bottle detection:

| Signal | Contribution |
|---|---|
| Body landmarks present (`landmarks is not None`) | `+0.5` |
| Bottle detected this frame or held last YOLO result (`bottle is not None`) | `+0.4` |
| Session calibration completed (`_calibration is not None`) | `+0.1` |
| **Total** | Clamped to `[0.0, 1.0]` |

Notes:

- This is a **session readiness / tracking composite**, not YOLO class confidence alone and not MediaPipe landmark visibility average.
- Camera-test frames use the same formula (calibration term is usually `0` until/unless calibration runs).
- YOLO’s per-detection confidence remains available on bottle checks via `measured_value` where applicable; it is **not** the same field as `tracking_confidence`.
- Low-confidence gate compares this composite to `MIN_TRACKING_CONFIDENCE`.

---

## 4. Backend: status fields, priority, and low-confidence gate

### 4.1 Additive FrameEvent fields

| Field | Required | Notes |
|---|---|---|
| `assessment_state` | yes | Existing; source of truth |
| `tracking_confidence` | yes | Composite above |
| `status_reason` | no | Fixed string enum; omit/`null` when N/A |
| `status_message` | no | Short actionable human string |

### 4.2 Fixed `status_reason` enum

**Backend may emit:**

```text
camera_unavailable
camera_read_failed
models_unavailable
internal_error
low_tracking_confidence
body_not_visible
bottle_not_visible
```

**Flutter client-only (never from Python):**

```text
backend_disconnected
protocol_error
```

### 4.3 Reason priority

When multiple conditions are true on one frame, emit the **highest-priority** reason only:

1. `camera_unavailable`
2. `camera_read_failed`
3. `models_unavailable`
4. `internal_error`
5. `low_tracking_confidence` (after debounce latch)
6. `body_not_visible`
7. `bottle_not_visible`

Lower-priority signals may still appear in checkpoint messages; they must not override a higher `status_reason`.

### 4.4 Low-confidence debounce and recovery

Config in `config.py`:

- `MIN_TRACKING_CONFIDENCE = 0.45`
- `LOW_CONFIDENCE_FRAMES_REQUIRED = 5`
- `LOW_CONFIDENCE_RECOVERY_FRAMES = 5`

**Enter latch:** after `LOW_CONFIDENCE_FRAMES_REQUIRED` consecutive frames with `tracking_confidence < MIN_TRACKING_CONFIDENCE`, force:

- `assessment_state = unable_to_assess`
- `status_reason = low_tracking_confidence` (unless a higher-priority reason applies)
- actionable `status_message`

**Exit latch:** after `LOW_CONFIDENCE_RECOVERY_FRAMES` consecutive frames at/above threshold, clear the low-confidence latch and resume normal evaluation.

### 4.5 Checkpoint / sequence behavior while unable

Applies to low-confidence latch **and** hard failures (models/camera/`internal_error`) that set `unable_to_assess`:

1. **Do not call** movement assessor `update()` while latched/unable for these reasons (freeze internal sequence counters/state).
2. **Preserve** previously `passed` checkpoints in the outgoing `checks` list (last validated set).
3. **Do not** emit new `passed` statuses while unable.
4. Incomplete / in-progress keys should surface as `not_assessed` or retained `in_progress` without promoting to `passed`.
5. Session summary metrics remain counts of checkpoint statuses — not a skill score.

### 4.6 Recovery / reset for sequence movements

| Event | Behavior |
|---|---|
| Low-confidence latch enter | Freeze assessor; keep prior `passed` checks; `assessment_state=unable_to_assess` |
| Low-confidence latch exit (recovery) | **Resume** assessor from frozen internal state — **no full sequence reset** |
| Models/camera/`internal_error` cleared and session still open | Resume from frozen state the same way when frames become usable again |
| User Stop / Cancel / new `start` command | Full session teardown; **new** session resets calibration + assessor |
| Unexpected practice exit (Flutter dispose) | Cancel + disconnect; backend session `close()` releases camera; next Start is a new session |

No mid-session auto-reset of a multi-step movement solely because confidence dipped and recovered.

### 4.7 Error mapping

| Condition | `status_reason` | Message guidance |
|---|---|---|
| Camera cannot open | `camera_unavailable` | Webcam busy or wrong index; close other apps |
| Frame read failed | `camera_read_failed` | Camera disconnected; reconnect and restart session |
| Pose/YOLO failed to load | `models_unavailable` | Models failed to load; check Python deps / weights |
| Unexpected exception in frame pipeline | `internal_error` | Unexpected assessment error; restart session; check backend logs |
| Body missing (when that is primary after higher priorities) | `body_not_visible` | Stand in frame; front-facing; full required body region |
| Bottle missing when required | `bottle_not_visible` | Opaque plastic practice bottle; improve lighting |

WebSocket invalid-command errors keep `type: error` JSON; optionally include `status_reason`/`status_message` on that payload when easy — Flutter maps malformed payloads to `protocol_error`.

---

## 5. Flutter UI / UX

### 5.1 Soft safety reminder — continuation behavior

- Trigger: only before **active practice Start** (practice shell), not when opening the Safety guide, tutorials, or camera test.
- Content: §20 operational limits (one user, front-facing, full body region, stable camera, lighting, opaque plastic bottle, no glass, clear area, no advanced tosses near people/breakables, stop on pain).
- **Continuation (soft):**
  - Primary **“I understand — continue”** → dismiss sheet and proceed to Start / allow Start.
  - Dismiss (barrier tap / close) → **also continues**; practice is not blocked.
  - Checkbox or button **“Don’t show again this launch”** → set in-memory flag for the app process; no DB write.
- Never a hard gate that requires ack for all future launches.

### 5.2 Banners and animations

- Practice + camera test: `AnimatedSwitcher` banner from `assessment_state`, then `status_reason` / client WS errors (respect priority when choosing copy).
- Actionable banner copy.
- `StatusChip`: cross-fade on status change.
- During `unable_to_assess`: suppress success animations; do not invent local `passed` checkpoints.
- Skip route-transition changes if they need a `GoRouter` rewrite.

### 5.3 Polish and accessibility

- Spacing / hit targets on practice, camera test, onboarding, safety.
- Semantics on Start/Stop and key status text.
- Preserve keyboard focus (Tab/Enter on primary actions).

### 5.4 Offline / mock messaging

The Flutter practice shell **currently** has an unreachable-backend fallback that shows labeled mock checkpoints (`_useOfflineMock`). Backend optional `ELIXR_USE_MOCK=1` remains a **dev** path.

**Phase 5 copy rules:**

- Do **not** claim offline mock as the primary or default assessment mode in onboarding, README, or manuscript “Implemented” claims.
- User-facing default narrative: **live CV assessment when the backend is running**.
- If the Flutter fallback remains in the build: keep the UI banner clearly labeled as a **demo fallback** (not live CV). Do not expand mock claims in thesis materials.
- Camera-test copy must not say “mock until Phase 3” if live readiness is already wired.

### 5.5 Client-side reason codes

```text
backend_disconnected
protocol_error
```

---

## 6. Documentation

### 6.1 Root README

Prerequisites (Windows desktop Flutter, Python 3.x, webcam), venv + `pip install -r backend/requirements.txt`, start backend, start Flutter Windows, WebSocket/health URLs, camera notes, troubleshooting (busy camera, models, disconnect, low confidence / unable), links to phase READMEs and `eval/`. Prefer live-assessment setup; mention `ELIXR_USE_MOCK` only under a short “Developer fallback” subsection if kept.

### 6.2 `backend/README_PHASE5.md`

Enum, priority, confidence formula summary, config knobs, freeze/resume rules, claims checklist pointer, demo stability checklist.

### 6.3 Manuscript claims checklist (tiers)

| Tier | Meaning | Examples |
|---|---|---|
| **Implemented** | Present in the running app/backend | Local login/register, onboarding, safety content, live WS assessment for enabled movements, SQLite sessions, history/progress, CSV export, soft safety reminder, low-confidence gate, reason codes |
| **Technically tested** | Measured or automated tests actually run with evidence | Unit tests for rules/debounce/recovery; bottle/FPS scripts **only where datasets/runs exist** |
| **User-evaluated** | Usability Likert / participant feedback (not CV ground truth unless experts) | Ease of use, clarity |
| **Not validated** | Must not be claimed as proven | Production accuracy for all movements, grip/rotation/contact, injury prevention, cloud, `.exe`, skill percentages, offline mock as validated assessment |

### 6.4 Ten-minute demo stability check

Label: **short demo stability check** (manual, reference laptop), not a formal soak.

**Documented tested environment (fill at run time):** OS build, laptop model/CPU/RAM, camera model/index, Flutter channel, Python version, backend command, lighting notes, practice bottle description.

**Checklist:**

1. Camera release after Stop / leave practice  
2. No duplicate WebSocket / double connection on Start  
3. Memory growth bounded over ~10 minutes  
4. UI remains responsive  
5. One Stop → one session save  
6. No new `passed` checkpoints while unable / low-confidence  
7. Unexpected practice exit cleans up session and camera  
8. Optional: backend stop → actionable `backend_disconnected` banner  

**Practical pass conditions:** no crash; single summary save; camera reopen on next Start; no sustained UI freeze (>2s); no new passes while unable; no multi‑GB RAM climb over 10 minutes.

---

## 7. Testing plan (expanded)

### 7.1 Backend unit tests

| Test | Expectation |
|---|---|
| Confidence formula unit (pure helper if extracted) | Body only → 0.5; body+bottle → 0.9; +calibration → 1.0 |
| Debounce enter | N−1 low frames → not latched; Nth → `unable_to_assess` + `low_tracking_confidence` |
| Debounce recovery | After recovery frames at/above threshold → latch cleared; assessor `update` runs again |
| Preserve passed checkpoints | Pre-seed passed check; while latched, payload still contains that `passed`; no *new* keys become `passed` |
| Assessor freeze | While latched, assessor state / frame counters do not advance |
| Reason priority | Camera failure beats low confidence when both would apply |
| `internal_error` | Forced exception path yields `unable_to_assess` + `internal_error` |
| Optional fields on schema | `FrameEvent` accepts omit/`null` for reason/message |

### 7.2 Flutter tests

| Test | Expectation |
|---|---|
| Frame parse missing optionals | JSON without `status_reason` / `status_message` still builds `FrameUpdate` |
| Frame parse with optionals | Fields populate on model |
| Client reason mapping | Disconnect → `backend_disconnected`; bad JSON → `protocol_error` |
| Banner/status helpers (if extracted) | `unable_to_assess` + `low_tracking_confidence` → low-confidence copy; suppress “success” styling |

### 7.3 Manual

Soft safety once per launch before practice Start; dismiss still continues; unexpected exit; demo stability checklist.

No new third-party profiler dependencies.

---

## 8. File touch list (indicative)

- `backend/config.py`, `backend/schemas/frame_event.py`, `backend/assessment/live_session.py`, camera/WS error paths as needed  
- Prefer small helper e.g. `backend/assessment/tracking_confidence.py` + `status_reasons.py` for formula/priority  
- `backend/tests/test_phase5_confidence.py` (or similar)  
- `lib/services/websocket_service.dart`, practice shell, camera test, `status_chip.dart`, onboarding/safety copy  
- Soft safety widget (small new file OK)  
- `README.md`, `backend/README_PHASE5.md`, light `LIMITATIONS.md` touch  
- `elixr_plan.md` Phase 5 frontmatter → completed when implementation finishes  

No new package dependencies without a separate ask.

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| Sticky unable after dips | Tunable enter/exit frame counts; recovery tests |
| Losing mid-sequence progress | Freeze assessor; resume without reset |
| Losing hard-won passes during unable | Preserve prior `passed` in emitted checks |
| Claim creep / mock narrative | Four-tier checklist; live CV default copy |
| Schema break | Additive optional fields only |

---

## 10. Approval record

- Thesis/docs: in-repo only  
- Safety: soft, session-only, before active practice Start; dismiss and continue both allow practice  
- Animations: banners + status chips; no router rewrite  
- Low confidence: UI + backend + threshold + debounce/recovery + priority + `internal_error`  
- Approach: thin polish pass  
- Post-spec revisions (2026-07-15): confidence formula, reason priority, preserve passed checkpoints, checkpoint/session metrics language, safety continuation, mock copy rules, sequence freeze/resume, expanded tests  
