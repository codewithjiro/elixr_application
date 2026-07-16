from typing import Literal, Optional

from pydantic import BaseModel, Field


class ClientCommand(BaseModel):
    action: Literal["start", "stop", "cancel"]
    movement_id: Optional[str] = None
    dominant_hand: Literal["left", "right"] = "right"
    mirror_camera: bool = True


class StartCommand(BaseModel):
    action: Literal["start"] = "start"
    movement_id: str = Field(..., min_length=1)
    dominant_hand: Literal["left", "right"] = "right"
    mirror_camera: bool = True
