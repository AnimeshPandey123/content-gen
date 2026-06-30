"""LLM-planned storyboard scene models."""

from pydantic import BaseModel, Field


class PlannedSceneSource(BaseModel):
    """Source reference returned by the storyboard LLM."""

    section: str = Field(min_length=1, description="Section title")
    page: int = Field(ge=1, description="1-based PDF page number")
    paragraph: int = Field(ge=1, description="1-based paragraph index")


class PlannedScene(BaseModel):
    """A single scene planned by Gemini before script generation."""

    goal: str = Field(min_length=1, description="What this scene should communicate")
    duration_seconds: float = Field(gt=0, le=30, description="Target on-screen duration")
    source: PlannedSceneSource


class StoryboardGenerationResponse(BaseModel):
    """Structured Gemini response for storyboard generation."""

    scenes: list[PlannedScene] = Field(
        min_length=1,
        max_length=20,
        description="Ordered storyboard scenes for the short video",
    )
