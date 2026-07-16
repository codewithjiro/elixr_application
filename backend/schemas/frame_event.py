from typing import Any, Optional, Union

from pydantic import BaseModel, Field


class CheckpointUpdate(BaseModel):
    key: str
    status: str
    message: str
    measured_value: Optional[Union[float, str]] = None
    expected_range: Optional[str] = None


class FrameEvent(BaseModel):
    type: str = "frame"
    movement_id: str
    assessment_state: str
    body_detected: bool
    bottle_detected: bool
    tracking_confidence: float = Field(ge=0.0, le=1.0)
    current_step: str
    checks: list[CheckpointUpdate] = Field(default_factory=list)
    frame_jpeg_base64: str
    camera_source: str = "placeholder"
    status_reason: str | None = None
    status_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
