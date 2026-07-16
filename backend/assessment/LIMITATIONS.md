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
