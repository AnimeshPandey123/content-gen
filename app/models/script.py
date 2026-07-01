"""Video script model."""

from pydantic import BaseModel, Field, computed_field


class ScriptShot(BaseModel):
    """Voice and overlay text for one storyboard camera shot."""

    shot_order: int = Field(ge=0, description="0-based shot order within the scene")
    voice: str = Field(min_length=1, description="Text spoken while this shot is on screen")
    overlay: str = Field(min_length=1, description="On-screen overlay text for this shot")


class ScriptScene(BaseModel):
    """Script entries for one storyboard scene, one per camera shot."""

    scene: int = Field(ge=1, description="1-based scene number")
    scene_id: str = Field(min_length=1, description="Storyboard scene identifier")
    shots: list[ScriptShot] = Field(min_length=1)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def voice(self) -> str:
        """Full scene narration (all shot voices concatenated for scene-level TTS)."""
        return " ".join(shot.voice.strip() for shot in self.shots if shot.voice.strip())

    @computed_field  # type: ignore[prop-decorator]
    @property
    def overlay(self) -> str:
        """Primary overlay label (first shot) for compatibility."""
        return self.shots[0].overlay


class Script(BaseModel):
    """Complete script for the short video."""

    scenes: list[ScriptScene] = Field(min_length=1)
