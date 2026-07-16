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
