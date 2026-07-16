from typing import Any, Optional

from pydantic import BaseModel, Field

from .frame_event import CheckpointUpdate


class SessionSummary(BaseModel):
    type: str = "session_summary"
    movement_id: str
    result_status: str
    duration_seconds: int
    attempt_count: int = 1
    passed_check_count: int = 0
    failed_check_count: int = 0
    not_assessed_count: int = 0
    detection_interruptions: int = 0
    assessment_version: str = "3.0"
    checks: list[CheckpointUpdate] = Field(default_factory=list)
    message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
