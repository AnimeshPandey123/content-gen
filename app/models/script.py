"""Video script model."""

from pydantic import BaseModel, Field


class ScriptScene(BaseModel):
    """Voice and overlay text for one storyboard scene."""

    scene: int = Field(ge=1, description="1-based scene number")
    scene_id: str = Field(min_length=1, description="Storyboard scene identifier")
    voice: str = Field(min_length=1, description="Text sent to TTS")
    overlay: str = Field(min_length=1, description="On-screen overlay text")
    duration: float = Field(gt=0, description="Scene duration in seconds")


class Script(BaseModel):
    """Complete script for the short video."""

    scenes: list[ScriptScene] = Field(min_length=1)
