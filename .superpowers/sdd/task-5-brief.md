### Task 5: Documentation + claims + demo checklist

**Files:**
- Modify: `README.md`
- Create: `backend/README_PHASE5.md`
- Modify: `backend/assessment/LIMITATIONS.md` (short Phase 5 note on confidence composite + unable freeze)
- Modify: `elixr_plan.md` frontmatter Phase 5 → completed

**Interfaces:**
- Consumes: implemented behavior from Tasks 1–4
- Produces: reproducible setup docs; four-tier claims; demo stability checklist with environment fields

- [ ] **Step 1: Replace root README**

Include: prerequisites, backend venv/install/run (`uvicorn`), Flutter Windows run, health/WS URLs from `lib/core/constants/websocket_constants.dart`, troubleshooting, links to phase READMEs + `eval/`, short Developer fallback for `ELIXR_USE_MOCK` (not primary).

- [ ] **Step 2: Write `backend/README_PHASE5.md`**

Include: confidence formula table, reason enum + priority, config knobs, freeze/resume rules, manuscript claims checklist (Implemented / Technically tested / User-evaluated / Not validated), **10-minute demo stability check** with environment blanks and practical pass conditions (camera release, duplicate connection, memory, UI responsiveness, duplicate saves, false-pass, unexpected exit).

- [ ] **Step 3: Sync LIMITATIONS + elixr_plan todo status**

- [ ] **Step 4: Commit (if git available)**

```bash
git add README.md backend/README_PHASE5.md backend/assessment/LIMITATIONS.md elixr_plan.md
git commit -m "docs(phase5): setup README, claims tiers, and demo stability checklist"
```

---

## Spec coverage checklist

| Spec item | Task |
|---|---|
| Confidence formula defined + used | 1, 2 |
| Reason enum + priority + `internal_error` | 1, 2 |
| Debounce enter/recovery | 1, 2 |
| Preserve passed; block new passes; freeze assessor | 1, 2 |
| Sequence resume without reset | 2, 4 manual |
| Soft safety continuation | 4 |
| Mock copy rules | 4, 5 |
| Animations banners/chips; no router rewrite | 4 |
| Flutter missing optional fields tests | 3 |
| Expanded backend/Flutter tests | 1–3 |
| README + PHASE5 + claims tiers + demo checklist | 5 |
| No new deps / thin polish | Global |

## Placeholder / consistency self-review

- No TBD steps; helpers named consistently (`compute_tracking_confidence`, `pick_status_reason`, `LowConfidenceGate`, `merge_checks_while_unable`).
- Commit steps gated on git availability.
- Package import in Dart tests must match `pubspec.yaml` `name` at implementation time.
