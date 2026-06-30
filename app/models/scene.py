"""Storyboard scene model."""

from pydantic import BaseModel, Field


class Scene(BaseModel):
    """A single scene in the video storyboard."""

    id: str
    section_id: str
    order: int = Field(ge=0)
    description: str
    duration_seconds: float = Field(gt=0, description="Target on-screen duration")
