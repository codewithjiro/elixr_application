from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "elixr-backend",
        "phase": 2,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
