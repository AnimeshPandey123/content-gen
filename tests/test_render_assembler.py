"""Unit tests for video assembly from rendered assets."""

from pathlib import Path

import pytest
from app.config import Settings
from app.models.render import SceneAssets
from app.render.assembler import VideoAssembler

from app.render.project import bootstrap_render_project
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
                    shot_screenshot_paths=[str(tmp_path / "scene01_shot01.png")],
                    screenshot_path=str(tmp_path / "scene01_shot01.png"),
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


def test_render_assembler_probes_audio_when_duration_missing(monkeypatch, tmp_path: Path) -> None:
    probed: list[str] = []

    class _FakeFFmpeg:
        def render_scene(self, **kwargs):
            kwargs["output_path"].write_text("clip", encoding="utf-8")

        def concat_clips(self, clip_paths, output_path):
            output_path.write_text("video", encoding="utf-8")

    monkeypatch.setattr(
        "app.render.assembler.probe_wav_duration",
        lambda path: probed.append(str(path)) or 5.5,
    )

    project = _render_project().model_copy(
        update={
            "project_dir": str(tmp_path),
            "scenes": [
                SceneAssets(
                    scene_number=1,
                    scene_id="scene-1",
                    shot_screenshot_paths=[str(tmp_path / "scene01_shot01.png")],
                    screenshot_path=str(tmp_path / "scene01_shot01.png"),
                    audio_path=str(tmp_path / "scene01.wav"),
                    subtitle_path=str(tmp_path / "scene01.ass"),
                ),
            ],
        },
    )
    Path(project.scenes[0].screenshot_path).write_text("png", encoding="utf-8")
    Path(project.scenes[0].audio_path).write_text("wav", encoding="utf-8")

    assembler = VideoAssembler(
        settings=Settings(output_dir=tmp_path),
        ffmpeg_renderer=_FakeFFmpeg(),
    )
    assembler.render(project)

    assert probed == [str(tmp_path / "scene01.wav")]


def test_render_splits_shot_durations_when_counts_mismatch(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, list[float]] = {}

    class _FakeFFmpeg:
        def render_scene(self, **kwargs):
            captured["durations"] = kwargs["shot_durations"]
            kwargs["output_path"].write_text("clip", encoding="utf-8")

        def concat_clips(self, clip_paths, output_path):
            output_path.write_text("video", encoding="utf-8")

    from app.models.bounding_box import BoundingBox
    from app.models.pipeline import ContentPlan, ScriptPlan, StoryboardResult
    from app.models.scene import Scene, SceneShot, SceneSource, SceneVisual
    from app.models.script import Script, ScriptScene, ScriptShot
    from app.models.section import Section
    from app.models.storyboard import Storyboard
    from tests.test_stages import _sample_document

    crop = BoundingBox(x=0, y=0, width=10, height=10)
    document = _sample_document()
    storyboard_scene = Scene(
        id="scene-1",
        section_id="sec-1",
        order=0,
        goal="Scene",
        duration_seconds=6.0,
        source=SceneSource(section="T", page=1, paragraph=1),
        shots=[
            SceneShot(
                order=0,
                goal="A",
                duration_seconds=2.0,
                page=1,
                paragraph=1,
                framing="wide",
                crop=crop,
            ),
            SceneShot(
                order=1,
                goal="B",
                duration_seconds=4.0,
                page=1,
                paragraph=1,
                framing="focus",
                crop=crop,
            ),
        ],
        visual=SceneVisual(page=1, crop=crop),
    )
    project = ScriptPlan(
        storyboard_result=StoryboardResult(
            content_plan=ContentPlan(
                document=document,
                selected_sections=[
                    Section(id="sec-1", title="T", content="Sample", page_numbers=[1]),
                ],
            ),
            storyboard=Storyboard(document_id=document.id, scenes=[storyboard_scene]),
        ),
        script=Script(
            scenes=[
                ScriptScene(
                    scene=1,
                    scene_id="scene-1",
                    shots=[
                        ScriptShot(shot_order=0, voice="Voice", overlay="Overlay"),
                    ],
                ),
            ],
        ),
    )
    render_project = bootstrap_render_project(project, settings=Settings(output_dir=tmp_path))
    render_project = render_project.model_copy(
        update={
            "scenes": [
                render_project.scenes[0].model_copy(
                    update={
                        "shot_screenshot_paths": [str(tmp_path / "only.png")],
                        "screenshot_path": str(tmp_path / "only.png"),
                        "audio_path": str(tmp_path / "scene01.wav"),
                        "audio_duration_seconds": 6.0,
                        "subtitle_path": str(tmp_path / "scene01.ass"),
                    },
                ),
            ],
        },
    )
    Path(render_project.scenes[0].audio_path).write_text("wav", encoding="utf-8")

    assembler = VideoAssembler(
        settings=Settings(output_dir=tmp_path),
        ffmpeg_renderer=_FakeFFmpeg(),
    )
    assembler.render(render_project)

    assert captured["durations"] == [6.0]


def test_render_raises_when_screenshot_assets_missing(tmp_path: Path) -> None:
    project = _render_project().model_copy(
        update={
            "project_dir": str(tmp_path),
            "scenes": [
                SceneAssets(
                    scene_number=1,
                    scene_id="scene-1",
                    audio_path=str(tmp_path / "scene01.wav"),
                    subtitle_path=str(tmp_path / "scene01.ass"),
                ),
            ],
        },
    )
    assembler = VideoAssembler(settings=Settings(output_dir=tmp_path))

    with pytest.raises(ValueError, match="missing screenshot assets"):
        assembler.render(project)


def test_render_raises_when_scene_assets_missing(tmp_path: Path) -> None:
    project = _render_project().model_copy(update={"project_dir": str(tmp_path)})
    assembler = VideoAssembler(settings=Settings(output_dir=tmp_path))

    with pytest.raises(ValueError, match="missing required assets"):
        assembler.render(project)
