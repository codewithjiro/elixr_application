# Task 5 Review Package
## FILE: README.md
```
# ELIXR — Windows Desktop Practice Assistant

ELIXR is a local Windows desktop app for beginner flairtending practice. Flutter provides the UI and SQLite session history; a local Python FastAPI backend owns the webcam and runs live computer-vision assessment over WebSocket.

**Default mode:** live CV assessment when the backend is running. Offline or mock paths are developer/demo fallbacks only — not the primary assessment mode.

## Prerequisites

| Component | Requirement |
|---|---|
| OS | Windows 10/11 (desktop target) |
| Flutter | Stable channel with Windows desktop enabled (`flutter doctor`) |
| Python | 3.10+ recommended |
| Hardware | Webcam; opaque plastic practice bottle; front-facing, well-lit setup |

## Quick start

### 1. Backend

```powershell
cd backend
python -m venv C:\elixr-venv
C:\elixr-venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

Verify readiness:

```text
GET http://127.0.0.1:8000/health
```

### 2. Flutter app

In a second terminal, from the repo root:

```powershell
flutter pub get
flutter run -d windows
```

Log in or register, complete onboarding, then use **Camera Test** or **Practice** with the backend running.

### 3. Endpoints (defaults)

Defined in `lib/core/constants/websocket_constants.dart`:

| Endpoint | URL |
|---|---|
| Health | `http://127.0.0.1:8000/health` |
| WebSocket | `ws://127.0.0.1:8000/ws` |

The Flutter client uses these defaults on localhost. Change host/port only if you also update the backend bind address and constants together.

## Camera and session notes

- Only the Python backend opens the webcam during an active session.
- One user, front-facing, full required body region visible, stable camera, good lighting, opaque plastic bottle (no glass).
- Stop or leave practice to release the camera before another app uses it.
- Session results use **checkpoint statuses** and session summary counts (`passed_check_count`, `failed_check_count`, `not_assessed_count`, `result_status`) — not skill percentages.

## Troubleshooting

| Symptom | Likely cause | What to try |
|---|---|---|
| Camera busy / cannot open | Another app holds the webcam | Close other camera apps; Stop practice; restart backend |
| `models_unavailable` | YOLO/MediaPipe failed to load | Re-run `pip install -r requirements.txt`; check backend console for weight/download errors |
| `camera_read_failed` | USB disconnect or driver glitch | Reconnect camera; Stop and Start a new session |
| `backend_disconnected` banner | Backend stopped or wrong port | Start uvicorn on `127.0.0.1:8000`; confirm `/health` responds |
| `low_tracking_confidence` / unable to assess | Body/bottle not stable in frame | Improve lighting; stand front-on; use opaque bottle; reduce motion blur |
| No new passes while unable | Expected Phase 5 behavior | Fix tracking; wait for recovery — prior **passed** checkpoints are preserved |
| Practice shows demo fallback UI | Backend unreachable | Start backend for live CV; fallback is labeled demo, not validated assessment |

Backend unit tests:

```powershell
cd backend
python -m unittest discover -s tests -p "test_*.py" -v
```

Flutter tests:

```powershell
flutter test
```

## Phase documentation

| Doc | Contents |
|---|---|
| [backend/README_PHASE0.md](backend/README_PHASE0.md) | Scope proof / POC |
| [backend/README_PHASE2.md](backend/README_PHASE2.md) | WebSocket protocol |
| [backend/README_PHASE3.md](backend/README_PHASE3.md) | Live CV movements |
| [backend/README_PHASE4.md](backend/README_PHASE4.md) | Persistence + evaluation scripts |
| [backend/README_PHASE5.md](backend/README_PHASE5.md) | Confidence gate, claims tiers, demo stability checklist |
| [backend/assessment/LIMITATIONS.md](backend/assessment/LIMITATIONS.md) | Movement and CV limitations |
| [backend/eval/](backend/eval/) | Bottle detection, expert agreement, FPS/latency, export |

## Developer fallback (not primary assessment)

For UI work without models or camera:

```powershell
set ELIXR_USE_MOCK=1
uvicorn main:app --host 127.0.0.1 --port 8000
```

The Flutter practice shell may also show a labeled offline mock when the backend is unreachable. Do **not** treat either path as validated assessment in demos or manuscript claims.

```
## FILE: backend\README_PHASE5.md
```
# ELIXR Phase 5 — Polish, Documentation, and Demo Readiness

Phase 5 adds low-confidence gating, `status_reason` / `status_message` on frame events, UI polish, soft safety reminders, and in-repo manuscript claim tiers plus a **10-minute demo stability check**.

**Language:** Use **checkpoint statuses** and **session result metrics** (`passed_check_count`, `failed_check_count`, `not_assessed_count`, `result_status`). Do not describe freezing “scores” or skill percentages.

---

## Tracking confidence (composite)

Computed each frame in `LiveAssessmentSession.next_frame_event` via `compute_tracking_confidence` (`assessment/tracking_confidence.py`):

| Signal | Contribution |
|---|---|
| Body landmarks present | `+0.5` |
| Bottle detected (this frame or last YOLO hold) | `+0.4` |
| Session calibration completed | `+0.1` |
| **Total** | Clamped to `[0.0, 1.0]` |

This is a **session readiness / tracking composite**, not YOLO class confidence alone and not MediaPipe landmark visibility average. Camera-test frames use the same formula (calibration term is usually `0` until calibration runs). YOLO per-detection confidence remains on bottle checks via `measured_value` where applicable.

Low-confidence gate compares this composite to `MIN_TRACKING_CONFIDENCE`.

---

## `status_reason` enum and priority

**Backend may emit** (`assessment/status_reasons.py`):

```text
camera_unavailable
camera_read_failed
models_unavailable
internal_error
low_tracking_confidence
body_not_visible
bottle_not_visible
```

**Flutter client-only** (never from Python):

```text
backend_disconnected
protocol_error
```

When multiple conditions apply on one frame, `pick_status_reason` emits the **highest-priority** reason only:

1. `camera_unavailable`
2. `camera_read_failed`
3. `models_unavailable`
4. `internal_error`
5. `low_tracking_confidence` (after debounce latch)
6. `body_not_visible`
7. `bottle_not_visible`

Lower-priority signals may still appear in checkpoint messages; they must not override a higher `status_reason`.

| Condition | `status_reason` | Message guidance |
|---|---|---|
| Camera cannot open | `camera_unavailable` | Webcam busy or wrong index; close other apps |
| Frame read failed | `camera_read_failed` | Camera disconnected; reconnect and restart session |
| Pose/YOLO failed to load | `models_unavailable` | Check Python deps / weights |
| Unexpected frame pipeline exception | `internal_error` | Restart session; check backend logs |
| Body missing (after higher priorities) | `body_not_visible` | Stand in frame; front-facing; full body region |
| Bottle missing when required | `bottle_not_visible` | Opaque plastic bottle; improve lighting |

Additive optional FrameEvent fields: `status_reason`, `status_message`. `assessment_state` remains the source of truth.

---

## Config knobs (`config.py`)

| Setting | Default | Role |
|---|---|---|
| `MIN_TRACKING_CONFIDENCE` | `0.45` | Threshold for low-confidence latch |
| `LOW_CONFIDENCE_FRAMES_REQUIRED` | `5` | Consecutive low frames to enter unable |
| `LOW_CONFIDENCE_RECOVERY_FRAMES` | `5` | Consecutive at/above-threshold frames to exit latch |

**Enter latch** (`LowConfidenceGate`): after `LOW_CONFIDENCE_FRAMES_REQUIRED` consecutive frames with `tracking_confidence < MIN_TRACKING_CONFIDENCE`:

- `assessment_state = unable_to_assess`
- `status_reason = low_tracking_confidence` (unless higher priority applies)
- actionable `status_message`

**Exit latch:** after `LOW_CONFIDENCE_RECOVERY_FRAMES` consecutive frames at/above threshold, clear latch and resume normal evaluation.

---

## Freeze and resume while unable

Applies to low-confidence latch **and** hard failures (models/camera/`internal_error`) that set `unable_to_assess`:

1. **Do not call** movement assessor `update()` while latched/unable — freeze internal sequence counters/state.
2. **Preserve** previously `passed` checkpoints in outgoing `checks` (`merge_checks_while_unable`).
3. **Do not emit** new `passed` statuses while unable.
4. Incomplete keys surface as `not_assessed` or retained `in_progress` without promoting to `passed`.

| Event | Behavior |
|---|---|
| Low-confidence enter | Freeze assessor; keep prior `passed` checks; `assessment_state=unable_to_assess` |
| Low-confidence exit (recovery) | **Resume** assessor from frozen state — **no full sequence reset** |
| Models/camera/`internal_error` cleared, session still open | Resume from frozen state when frames become usable |
| User Stop / Cancel / new `start` | Full teardown; **new** session resets calibration + assessor |
| Unexpected practice exit (Flutter dispose) | Cancel + disconnect; backend `close()` releases camera; next Start is new session |

No mid-session auto-reset of a multi-step movement solely because confidence dipped and recovered.

---

## Manuscript claims checklist (four tiers)

Use these tiers in thesis/manuscript materials. Do not claim features in a higher tier unless evidence exists.

| Tier | Meaning | Examples |
|---|---|---|
| **Implemented** | Present in the running app/backend | Local login/register, onboarding, safety content, live WS assessment for enabled movements, SQLite sessions, history/progress, CSV export, soft safety reminder, low-confidence gate, reason codes |
| **Technically tested** | Automated tests or measured scripts with evidence | Unit tests for confidence/debounce/recovery/freeze/priority; bottle/FPS scripts **only where datasets/runs exist** (`backend/eval/`) |
| **User-evaluated** | Usability Likert / participant feedback (not CV ground truth unless experts) | Ease of use, clarity of feedback |
| **Not validated** | Must **not** be claimed as proven | Production accuracy for all movements, grip/rotation/contact, injury prevention, cloud deploy, `.exe` packaging, skill percentages, offline mock as validated assessment |

**Mock copy rule:** Default narrative is **live CV when backend is running**. Flutter offline mock and `ELIXR_USE_MOCK=1` are dev/demo fallbacks — do not list them under **Implemented** as primary assessment or under **Technically tested** without explicit labeled-demo evidence.

---

## 10-minute demo stability check

**Label:** short **demo stability check** (manual, reference laptop) — **not** a formal soak test.

Fill the environment block at run time before claiming “tested on reference hardware.”

### Tested environment (fill at run time)

| Field | Value |
|---|---|
| OS build | |
| Laptop model / CPU / RAM | |
| Camera model / index | |
| Flutter channel / version | |
| Python version | |
| Backend command | `uvicorn main:app --host 127.0.0.1 --port 8000` |
| Lighting notes | |
| Practice bottle description | |

### Checklist

| # | Check | Pass condition |
|---|---|---|
| 1 | Camera release after Stop / leave practice | Next Start opens camera; no “busy device” without closing other apps |
| 2 | No duplicate WebSocket on Start | Single active connection; no double frame streams or duplicate session summaries |
| 3 | Memory over ~10 minutes | No multi‑GB RAM climb; growth bounded during continuous practice |
| 4 | UI responsiveness | No sustained freeze **> 2 s** during normal use |
| 5 | One Stop → one session save | Exactly one summary persisted per completed Stop (no duplicate rows for one stop) |
| 6 | No false-pass while unable | No **new** `passed` checkpoints during `unable_to_assess` / low-confidence latch |
| 7 | Unexpected practice exit | Navigate away or close practice without Stop → camera released; backend session cleaned up |
| 8 | Optional: backend stop mid-session | Flutter shows actionable `backend_disconnected` banner |

### Practical pass (all required)

- No crash during the 10-minute window
- Single summary save per intentional Stop
- Camera reopens on next Start
- No sustained UI freeze (> 2 s)
- No new passes while unable
- No multi‑GB RAM climb over 10 minutes

Record pass/fail and notes in your demo log; attach environment table when citing stability in manuscript materials.

---

## Run and tests

Same as Phase 3/4:

```powershell
cd backend
C:\elixr-venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

```powershell
flutter run -d windows
```

Phase 5 backend tests:

```powershell
cd backend
python -m unittest discover -s tests -p "test_phase5*.py" -v
```

See also [LIMITATIONS.md](assessment/LIMITATIONS.md) and root [README.md](../README.md).

```
## FILE: backend\assessment\LIMITATIONS.md
```
# Movement Assessment — Known Limitations (Phase 3 + Phase 5)

## Phase 5 — tracking confidence and unable freeze

`tracking_confidence` is a per-frame **composite** (body + bottle + calibration), not YOLO class score alone. When confidence stays below `MIN_TRACKING_CONFIDENCE` for debounced consecutive frames, the session enters `unable_to_assess` with `status_reason=low_tracking_confidence`. While unable (including camera/model hard failures), the movement assessor is **frozen**, prior **passed** checkpoints are **preserved**, and **no new passes** are emitted; recovery **resumes** the sequence without a full reset. See `backend/README_PHASE5.md`.

Operational constraints from `elixr_plan.md` §20 apply to every movement:
one user, front-facing camera, full required body region visible, stable placement,
sufficient lighting, opaque plastic practice bottle (no glass), uncluttered background.

Thresholds in `config.py` are **prototype defaults**. Expert-rated recordings and
threshold refinement belong to Phase 4 — not claimed as validated accuracy here.

## Shared failure modes

| Condition | System behavior |
|---|---|
| Required landmarks missing | `Unable to Assess` / `not_assessed` |
| Bottle required but undetected | `Unable to Assess` on bottle checks |
| Calibration never completes | Session stays in `calibrating` |
| YOLO miss on transparent / blurred bottle | Proximity / visibility fail open to `not_assessed` |
| Fast motion blur | Prefer slow beginner pace; otherwise `Unable to Assess` |
| Depth / contact / grip / rotation | **Not assessed** — never claimed |

## Per-movement notes

### Ready Stance / Balanced Stance Hold
- Ankle/hip occlusion or kneeling clothing hides landmarks → unable.
- Stance-width ratios assume standing face-on; side view invalidates rules.
- Balanced hold jitter is 2D torso sway only — not true balance.

### Bent-Arm Preparation / Arm Extension / Toss Preparation
- Elbow angle is 2D; foreshortening can mis-read extension.
- Bottle–wrist proximity ≠ grip verification.
- Arm Extension needs bent start then clear extension + hold.

### Basic Bottle Hold / Front / Side Lift / Controlled Lowering
- Height thresholds use normalized image `y` after calibration framing — distance to camera changes absolute pixel meaning; keep similar framing session-to-session.
- Side lift uses lateral wrist offset relative to shoulder — crossing arms confuses path.
- Lowering “controlled duration” is frame-count based, not true velocity physics.

### Basic Hand-to-Hand Transfer (highest risk)
- Occlusion during mid-transfer often drops the bottle class → visibility ratio → `not_assessed`.
- Does not verify catch success, contact, or which fingers hold the bottle.
- If field reliability stays poor, replace with `neutral_return_position` per plan fallback.
- Do not treat synthetic unit tests as expert agreement.

## Recorded attempts

Phase 3 includes unit tests with synthetic landmarks/boxes. Correct/incorrect **webcam
recordings** and expert labeling are Phase 4 evaluation tasks.

```
## FILE: elixr_plan.md (frontmatter excerpt)
```
---
name: ELIXR Realistic App Architecture
summary: Build ELIXR as a Windows desktop training assistant with Flutter for the interface, SQLite for local accounts and session history, and a local FastAPI + WebSocket Python backend for webcam processing. The MVP will assess 10 selected beginner preparation and bottle-control movements using YOLO11n bottle detection, MediaPipe Pose, normalized geometry, and multi-frame rule-based state machines. Advanced flair tricks and exact grip recognition are tutorial-only.
todos:
  - id: phase0-scope-proof
    content: "Phase 0: Freeze the scope and prove one movement first: webcam, pose, bottle detection, calibration, arm-extension rules, and measurable FPS/latency"
    status: completed
  - id: phase1-flutter-foundation
    content: "Phase 1: Replace main.dart; build login/register, onboarding, dashboard, camera test, movement catalog, practice shell, history, progress, safety, and settings using SQLite"
    status: completed
  - id: phase2-backend-connection
    content: "Phase 2: Create FastAPI /health and /ws; stream annotated frames and structured mock assessment events to Flutter"
    status: completed
  - id: phase3-cv-assessment
    content: "Phase 3: Add OpenCV, YOLO11n bottle detection, MediaPipe Pose, calibration, smoothing, state machines, and rules for the 10 selected assessments"
    status: completed
  - id: phase4-persistence-testing
    content: "Phase 4: Save session/checkpoint results; build history/progress; measure bottle detection, expert agreement, FPS, latency, and usability"
    status: completed
  - id: phase5-polish-documentation
    content: "Phase 5: Improve error handling, performance, UI consistency, safety notices, README, and thesis-ready limitations; defer packaging and non-core features"
    status: completed
isProject: true
---

# ELIXR Development Plan

## 1. Project Positioning

ELIXR is a **Windows desktop beginner practice assistant**, not a full AI flairtending instructor.
```

