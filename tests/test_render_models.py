"""Unit tests for render asset models."""

import pytest
from app.models.render import SceneAssets, SceneAudio, SceneClip, SceneScreenshot, SceneSubtitle
from pydantic import ValidationError


def test_render_project_with_screenshots_updates_scene_assets() -> None:
    from tests.test_render_project import _render_project

    project = _render_project()
    updated = project.with_screenshots(
        [SceneScreenshot(scene_id="scene-1", image_path="/tmp/scene01.png")],
    )
    assert updated.scenes[0].screenshot_path == "/tmp/scene01.png"


def test_render_project_with_audio_updates_scene_assets() -> None:
    from tests.test_render_project import _render_project

    project = _render_project()
    updated = project.with_audio(
        [
            SceneAudio(
                scene_id="scene-1",
                audio_path="/tmp/scene01.wav",
                duration_seconds=5.0,
            ),
        ],
    )
    assert updated.scenes[0].audio_path == "/tmp/scene01.wav"
    assert updated.scenes[0].audio_duration_seconds == 5.0


def test_render_project_with_subtitles_updates_scene_assets() -> None:
    from tests.test_render_project import _render_project

    project = _render_project()
    updated = project.with_subtitles(
        [SceneSubtitle(scene_id="scene-1", subtitle_path="/tmp/scene01.ass")],
    )
    assert updated.scenes[0].subtitle_path == "/tmp/scene01.ass"


def test_render_project_with_clips_updates_scene_assets() -> None:
    from tests.test_render_project import _render_project

    project = _render_project()
    updated = project.with_clips(
        [SceneClip(scene_id="scene-1", clip_path="/tmp/scene01.mp4")],
    )
    assert updated.scenes[0].clip_path == "/tmp/scene01.mp4"


def test_render_project_with_video_path() -> None:
    from tests.test_render_project import _render_project

    project = _render_project()
    updated = project.with_video_path("/tmp/final.mp4")
    assert updated.video_path == "/tmp/final.mp4"


def test_scene_assets_requires_scene_number() -> None:
    with pytest.raises(ValidationError):
        SceneAssets(scene_number=0, scene_id="scene-1")
