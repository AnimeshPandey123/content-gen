"""Storyboard scene model."""

from pydantic import BaseModel, Field

from app.models.bounding_box import BoundingBox


class SceneSource(BaseModel):
    """Where a scene draws its content from in the document."""

    section: str = Field(min_length=1, description="Section title")
    page: int = Field(ge=1, description="1-based PDF page number")
    paragraph: int = Field(ge=1, description="1-based paragraph index")


class SceneVisual(BaseModel):
    """Visual framing for a scene."""

    page: int = Field(ge=1, description="1-based PDF page number")
    crop: BoundingBox = Field(description="PDF crop region in page coordinates")


class Scene(BaseModel):
    """A single scene in the video storyboard."""

    id: str
    section_id: str
    order: int = Field(ge=0)
    goal: str = Field(min_length=1, description="What this scene should communicate")
    duration_seconds: float = Field(gt=0, description="Target on-screen duration")
    source: SceneSource
    visual: SceneVisual
