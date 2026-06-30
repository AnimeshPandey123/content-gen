"""LLM-decided pacing and structure for a short video."""

from pydantic import BaseModel, Field


class VideoPlan(BaseModel):
    """Pacing budget chosen by the storyboard LLM."""

    target_video_duration_seconds: float = Field(
        gt=0,
        le=120,
        description="Target total video duration including the title page",
    )
    title_page_duration_seconds: float = Field(
        gt=0,
        le=15,
        description="Duration of the opening title-page scene",
    )
    min_scene_duration_seconds: float = Field(
        gt=0,
        le=15,
        description="Shortest allowed scene duration when fitting the budget",
    )
