"""LLM script generation response models."""

from pydantic import BaseModel, Field


class GeneratedScriptShot(BaseModel):
    """A single shot script returned by Gemini."""

    shot_order: int = Field(ge=0, description="0-based shot order within the scene")
    voice: str = Field(min_length=1, description="Text spoken during this shot")
    overlay: str = Field(min_length=1, description="On-screen overlay text for this shot")


class GeneratedScriptScene(BaseModel):
    """Script for one storyboard scene returned by Gemini."""

    scene: int = Field(ge=1, description="1-based scene number")
    shots: list[GeneratedScriptShot] = Field(
        min_length=1,
        description="One script entry per storyboard shot in the scene",
    )


class ScriptGenerationResponse(BaseModel):
    """Structured Gemini response for script generation."""

    scenes: list[GeneratedScriptScene] = Field(
        min_length=1,
        max_length=20,
        description="Ordered script scenes matching the storyboard",
    )
