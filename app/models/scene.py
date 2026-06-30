"""Storyboard scene model."""

from pydantic import BaseModel, Field


class Scene(BaseModel):
    """A single scene in the video storyboard."""

    id: str
    section_id: str
    order: int = Field(ge=0)
    goal: str = Field(min_length=1, description="What this scene should communicate")
    duration_seconds: float = Field(gt=0, description="Target on-screen duration")
    source: str = Field(min_length=1, description="Section or content source for this scene")
    screenshot: str = Field(min_length=1, description="What visual to capture on screen")
    narration: str = Field(min_length=1, description="Planned voiceover script")
    caption: str = Field(min_length=1, description="Planned on-screen caption")
    paragraph_index: int | None = Field(
        default=None,
        ge=1,
        description="1-based paragraph index to capture for this scene",
    )
