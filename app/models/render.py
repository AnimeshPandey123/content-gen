"""Render artifact models for the video production pipeline."""

from pydantic import BaseModel, Field


class SceneScreenshot(BaseModel):
    """Cropped PNG screenshot for a storyboard scene."""

    scene_id: str
    image_path: str = Field(min_length=1)


class SceneAudio(BaseModel):
    """Generated narration audio for a scene."""

    scene_id: str
    audio_path: str = Field(min_length=1)
    duration_seconds: float = Field(gt=0)


class SceneSubtitle(BaseModel):
    """ASS subtitle file for a scene."""

    scene_id: str
    subtitle_path: str = Field(min_length=1)


class SceneClip(BaseModel):
    """Rendered video clip for a single scene."""

    scene_id: str
    clip_path: str = Field(min_length=1)


class RenderArtifacts(BaseModel):
    """All deterministic media assets produced before final mux."""

    project_dir: str
    screenshots: list[SceneScreenshot] = Field(min_length=1)
    audio_files: list[SceneAudio] = Field(min_length=1)
    subtitle_files: list[SceneSubtitle] = Field(min_length=1)
    scene_clips: list[SceneClip] = Field(min_length=1)
    video_path: str = Field(min_length=1)
