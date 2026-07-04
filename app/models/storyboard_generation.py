"""LLM-planned storyboard scene models."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models.video_plan import VideoPlan

CameraFraming = Literal["wide", "focus", "highlight"]


class PlannedSceneSource(BaseModel):
    """Source reference returned by the storyboard LLM."""

    section: str = Field(min_length=1, description="Section title")
    page: int = Field(ge=1, description="1-based PDF page number")
    paragraph: int = Field(ge=1, description="1-based paragraph index")


class PlannedShot(BaseModel):
    """A camera shot planned within a storyboard scene."""

    goal: str = Field(min_length=1, description="What this camera shot should show")
    duration_seconds: float = Field(gt=0, le=30, description="On-screen duration for this shot")
    visual: str | None = Field(
        default=None,
        description='Detected figure or table label, e.g. "Figure 3" or "Table 1"',
    )
    page: int | None = Field(default=None, ge=1, description="1-based PDF page number")
    paragraph: int | None = Field(default=None, ge=1, description="1-based paragraph index")
    framing: CameraFraming | None = Field(
        default=None,
        description="Camera framing: wide, focus, or highlight",
    )
    marker_highlight: bool = Field(
        default=False,
        description="Draw a marker highlight on the paragraph or visual bbox during this shot",
    )

    @model_validator(mode="after")
    def _visual_or_framing(self) -> "PlannedShot":
        if self.visual:
            return self
        if self.page is None or self.paragraph is None or self.framing is None:
            raise ValueError(
                "Either visual or page, paragraph, and framing are required for each shot",
            )
        return self


class PlannedScene(BaseModel):
    """A single scene planned by Gemini before script generation."""

    goal: str = Field(min_length=1, description="What this scene should communicate")
    duration_seconds: float = Field(gt=0, le=30, description="Target on-screen duration")
    source: PlannedSceneSource
    shots: list[PlannedShot] = Field(
        min_length=1,
        description="LLM-planned camera shots; one entry per on-screen frame",
    )


class StoryboardGenerationResponse(BaseModel):
    """Structured Gemini response for storyboard generation."""

    plan: VideoPlan = Field(description="LLM-chosen pacing and duration budget")
    scenes: list[PlannedScene] = Field(
        min_length=1,
        description="Ordered content scenes (title page is added automatically)",
    )
