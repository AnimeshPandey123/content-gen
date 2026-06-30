"""Unit tests for video assembly from rendered assets."""

from pathlib import Path

import pytest
from app.config import Settings
from app.models.render import SceneAssets
from app.render.assembler import VideoAssembler

from tests.test_render_project import _render_project


def test_render_assembles_scene_clips_and_final_video(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []

    class _FakeFFmpeg:
        def render_scene(self, **kwargs):
            calls.append("scene")
            kwargs["output_path"].write_text("clip", encoding="utf-8")

        def concat_clips(self, clip_paths, output_path):
            calls.append("concat")
            output_path.write_text("video", encoding="utf-8")

    project = _render_project().model_copy(
        update={
            "project_dir": str(tmp_path),
            "scenes": [
                SceneAssets(
                    scene_number=1,
                    scene_id="scene-1",
                    screenshot_path=str(tmp_path / "scene01.png"),
                    audio_path=str(tmp_path / "scene01.wav"),
                    audio_duration_seconds=5.0,
                    subtitle_path=str(tmp_path / "scene01.ass"),
                ),
            ],
        },
    )

    fake_ffmpeg = _FakeFFmpeg()
    assembler = VideoAssembler(
        settings=Settings(output_dir=tmp_path),
        ffmpeg_renderer=fake_ffmpeg,
    )
    result = assembler.render(project)

    assert calls == ["scene", "concat"]
    assert result.video_path is not None
    assert Path(result.video_path).exists()
    assert result.scenes[0].clip_path is not None


def test_render_raises_when_scene_assets_missing(tmp_path: Path) -> None:
    project = _render_project().model_copy(update={"project_dir": str(tmp_path)})
    assembler = VideoAssembler(settings=Settings(output_dir=tmp_path))

    with pytest.raises(ValueError, match="missing required assets"):
        assembler.render(project)
