"""LLM-planned storyboard scene models."""

from pydantic import BaseModel, Field


class PlannedScene(BaseModel):
    """A single scene planned by Gemini before asset generation."""

    goal: str = Field(min_length=1, description="What this scene should communicate")
    duration_seconds: float = Field(gt=0, le=30, description="Target on-screen duration")
    source: str = Field(min_length=1, description="Section title this scene draws from")
    screenshot: str = Field(
        min_length=1,
        description="What visual to capture from the document",
    )
    paragraph_index: int = Field(ge=1, description="1-based paragraph index for the screenshot")
    narration: str = Field(min_length=1, description="Voiceover script for this scene")
    caption: str = Field(min_length=1, description="On-screen caption text for this scene")


class StoryboardGenerationResponse(BaseModel):
    """Structured Gemini response for storyboard generation."""

    scenes: list[PlannedScene] = Field(
        min_length=1,
        max_length=20,
        description="Ordered storyboard scenes for the short video",
    )
