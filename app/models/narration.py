"""Narration script model."""

from pydantic import BaseModel, Field


class Narration(BaseModel):
    """Voiceover text aligned to a storyboard scene."""

    scene_id: str
    text: str = Field(min_length=1)
    estimated_duration_seconds: float = Field(gt=0)
