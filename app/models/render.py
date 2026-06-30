"""Render asset models for the video production pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.models.pipeline import ScriptPlan


class SceneScreenshot(BaseModel):
    """Cropped PNG screenshot for a storyboard scene shot."""

    scene_id: str
    shot_order: int = Field(default=0, ge=0)
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


class SceneAssets(BaseModel):
    """Reusable media assets for one storyboard scene."""

    scene_number: int = Field(ge=1, description="1-based scene number")
    scene_id: str = Field(min_length=1)
    shot_screenshot_paths: list[str] = Field(default_factory=list)
    screenshot_path: str | None = None
    audio_path: str | None = None
    audio_duration_seconds: float | None = Field(default=None, gt=0)
    subtitle_path: str | None = None
    clip_path: str | None = None


class RenderProject(BaseModel):
    """Inspectable project folder that accumulates rendering assets."""

    script_plan: ScriptPlan
    project_dir: str
    storyboard_path: str
    scenes: list[SceneAssets] = Field(min_length=1)
    video_path: str | None = None

    def with_screenshots(self, screenshots: list[SceneScreenshot]) -> RenderProject:
        by_scene: dict[str, list[SceneScreenshot]] = {}
        for item in screenshots:
            by_scene.setdefault(item.scene_id, []).append(item)

        def _update(scene: SceneAssets) -> SceneAssets:
            scene_shots = sorted(by_scene.get(scene.scene_id, []), key=lambda item: item.shot_order)
            paths = [item.image_path for item in scene_shots]
            return scene.model_copy(
                update={
                    "shot_screenshot_paths": paths,
                    "screenshot_path": paths[0] if paths else None,
                },
            )

        return self._update_scenes(_update)

    def with_audio(self, audio_files: list[SceneAudio]) -> RenderProject:
        paths = {item.scene_id: item.audio_path for item in audio_files}
        durations = {item.scene_id: item.duration_seconds for item in audio_files}
        return self._update_scenes(
            lambda scene: scene.model_copy(
                update={
                    "audio_path": paths[scene.scene_id],
                    "audio_duration_seconds": durations[scene.scene_id],
                },
            ),
        )

    def with_subtitles(self, subtitle_files: list[SceneSubtitle]) -> RenderProject:
        paths = {item.scene_id: item.subtitle_path for item in subtitle_files}
        return self._update_scenes(
            lambda scene: scene.model_copy(update={"subtitle_path": paths[scene.scene_id]}),
        )

    def with_clips(self, scene_clips: list[SceneClip]) -> RenderProject:
        paths = {item.scene_id: item.clip_path for item in scene_clips}
        return self._update_scenes(
            lambda scene: scene.model_copy(update={"clip_path": paths[scene.scene_id]}),
        )

    def with_video_path(self, video_path: str) -> RenderProject:
        return self.model_copy(update={"video_path": video_path})

    def _update_scenes(self, updater) -> RenderProject:
        return self.model_copy(update={"scenes": [updater(scene) for scene in self.scenes]})
