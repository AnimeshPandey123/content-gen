"""Storyboard aggregate model."""

from pydantic import BaseModel, Field

from app.models.scene import Scene
from app.models.timeline import VideoTimeline
from app.models.video_plan import VideoPlan


class Storyboard(BaseModel):
    """Ordered collection of scenes derived from document content."""

    document_id: str
    scenes: list[Scene] = Field(min_length=1)
    plan: VideoPlan | None = Field(
        default=None,
        description="LLM-decided pacing budget for this video",
    )
    timeline: VideoTimeline | None = Field(
        default=None,
        description="Global time-based timeline across all scenes",
    )
