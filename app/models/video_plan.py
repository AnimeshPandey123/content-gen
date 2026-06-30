"""LLM-decided pacing and structure for a short video."""

from pydantic import BaseModel, Field


class VideoPlan(BaseModel):
    """Pacing budget chosen by the storyboard LLM."""

    target_video_duration_seconds: float = Field(
        gt=0,
        le=120,
        description="Target total video duration including title and closing scenes",
    )
    title_page_duration_seconds: float = Field(
        gt=0,
        le=15,
        description="Duration of the opening title-page scene",
    )
    closing_scene_duration_seconds: float = Field(
        gt=0,
        le=15,
        description="Duration of the automatic closing takeaway scene",
    )
    min_scene_duration_seconds: float = Field(
        gt=0,
        le=15,
        description="Shortest allowed scene duration when fitting the budget",
    )
