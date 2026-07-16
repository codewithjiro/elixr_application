"""WebSocket endpoint: live CV frames + structured assessment events."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from assessment.live_session import create_session
from schemas.commands import ClientCommand

router = APIRouter()

# Target ~10 fps for assessment WebSocket updates
FRAME_INTERVAL_SEC = 0.1


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    session: Optional[Any] = None
    stream_task: Optional[asyncio.Task] = None
    stop_requested = asyncio.Event()

    async def stop_stream() -> Optional[dict]:
        nonlocal session, stream_task
        stop_requested.set()
        summary_payload = None
        if stream_task is not None:
            stream_task.cancel()
            try:
                await stream_task
            except asyncio.CancelledError:
                pass
            stream_task = None
        if session is not None:
            summary_payload = session.build_summary().to_dict()
            session.close()
            session = None
        stop_requested.clear()
        return summary_payload

    async def stream_frames() -> None:
        assert session is not None
        try:
            while not stop_requested.is_set():
                t0 = time.perf_counter()
                event = await asyncio.to_thread(session.next_frame_event)
                await websocket.send_json(event.to_dict())
                # Sleep only the remainder of the budget so slow CV frames
                # do not add a fixed extra 100ms (that grew camera backlog).
                elapsed = time.perf_counter() - t0
                await asyncio.sleep(max(0.0, FRAME_INTERVAL_SEC - elapsed))
        except asyncio.CancelledError:
            raise
        except Exception:
            # Connection gone or encode error — exit quietly
            return

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
                command = ClientCommand.model_validate(payload)
            except (json.JSONDecodeError, ValidationError) as exc:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Invalid command: {exc}",
                    }
                )
                continue

            if command.action == "start":
                if not command.movement_id:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "movement_id is required for start",
                        }
                    )
                    continue

                await stop_stream()
                try:
                    session = create_session(
                        movement_id=command.movement_id,
                        dominant_hand=command.dominant_hand,
                        mirror_camera=command.mirror_camera,
                    )
                except ValueError as exc:
                    await websocket.send_json(
                        {"type": "error", "message": str(exc)}
                    )
                    continue
                stop_requested.clear()
                stream_task = asyncio.create_task(stream_frames())
                await websocket.send_json(
                    {
                        "type": "session_started",
                        "movement_id": command.movement_id,
                        "camera_source": session.camera_source,
                        "message": "Live CV assessment stream started (Phase 3).",
                    }
                )

            elif command.action in ("stop", "cancel"):
                summary = await stop_stream()
                if summary is not None and command.action == "stop":
                    await websocket.send_json(summary)
                else:
                    await websocket.send_json(
                        {
                            "type": "session_cancelled"
                            if command.action == "cancel"
                            else "session_summary",
                            "movement_id": summary["movement_id"] if summary else None,
                            "result_status": "cancelled"
                            if command.action == "cancel"
                            else "not_assessed",
                            "duration_seconds": summary["duration_seconds"]
                            if summary
                            else 0,
                            "attempt_count": 0,
                            "passed_check_count": 0,
                            "failed_check_count": 0,
                            "not_assessed_count": 0,
                            "detection_interruptions": 0,
                            "checks": [],
                        }
                    )

    except WebSocketDisconnect:
        pass
    finally:
        await stop_stream()
