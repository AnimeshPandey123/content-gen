"""LLM script generation response models."""

from pydantic import BaseModel, Field


class GeneratedScriptScene(BaseModel):
    """A single scene script returned by Gemini."""

    scene: int = Field(ge=1, description="1-based scene number")
    voice: str = Field(min_length=1, description="Text sent to TTS")
    overlay: str = Field(min_length=1, description="On-screen overlay text")
    duration: float = Field(gt=0, le=30, description="Scene duration in seconds")


class ScriptGenerationResponse(BaseModel):
    """Structured Gemini response for script generation."""

    scenes: list[GeneratedScriptScene] = Field(
        min_length=1,
        max_length=20,
        description="Ordered script scenes matching the storyboard",
    )
