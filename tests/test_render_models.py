"""Unit tests for render artifact models."""

import pytest
from app.models.render import RenderArtifacts, SceneAudio, SceneClip, SceneSubtitle
from pydantic import ValidationError


def test_render_artifacts_require_assets() -> None:
    with pytest.raises(ValidationError):
        RenderArtifacts(
            project_dir="output/proj",
            screenshots=[],
            audio_files=[SceneAudio(scene_id="s1", audio_path="/tmp/a.wav", duration_seconds=1.0)],
            subtitle_files=[
                SceneSubtitle(scene_id="s1", subtitle_path="/tmp/s.ass"),
            ],
            scene_clips=[SceneClip(scene_id="s1", clip_path="/tmp/c.mp4")],
            video_path="/tmp/final.mp4",
        )
