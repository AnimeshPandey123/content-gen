"""Unit tests for ASS subtitle asset generation."""

from pathlib import Path

from app.config import Settings
from app.models.render import SceneAudio
from app.render.project import bootstrap_render_project
from app.render.subtitles import SubtitleGenerator
from app.services.stages.subtitle_generation import SubtitleGenerationStage
from app.services.stages.voice_generation import VoiceGenerationStage

from tests.test_render_project import _render_project, _script_plan


def test_build_ass_includes_karaoke_words() -> None:
    generator = SubtitleGenerator(settings=Settings())
    script_scene = _render_project().script_plan.script.scenes[0]
    content = generator.build_ass(script_scene, duration_seconds=4.0)

    assert "[Script Info]" in content
    assert "THIS" in content or "VOICE" in content
    assert "\\kf" in content


def test_produce_writes_scene01_ass(tmp_path: Path) -> None:
    project = bootstrap_render_project(
        _script_plan(),
        settings=Settings(output_dir=tmp_path),
    )
    generator = SubtitleGenerator(settings=Settings(output_dir=tmp_path))
    audio_files = [
        SceneAudio(scene_id="scene-1", audio_path=str(tmp_path / "a.wav"), duration_seconds=4.0),
    ]
    subtitles = generator.produce(project, audio_files)

    assert subtitles[0].subtitle_path.endswith("scene01.ass")
    assert Path(subtitles[0].subtitle_path).exists()


def test_subtitle_generation_stage_updates_project_assets(tmp_path: Path) -> None:
    project = bootstrap_render_project(
        _script_plan(),
        settings=Settings(output_dir=tmp_path),
    )
    voiced = VoiceGenerationStage(
        settings=Settings(output_dir=tmp_path, voice_synthesizer="silent"),
    ).run(project)
    result = SubtitleGenerationStage(settings=Settings(output_dir=tmp_path)).run(voiced)

    assert result.scenes[0].subtitle_path is not None


def test_build_ass_falls_back_to_overlay_when_voice_empty() -> None:
    from app.models.script import ScriptScene

    generator = SubtitleGenerator(settings=Settings())
    script_scene = ScriptScene(
        scene=1,
        scene_id="scene-1",
        voice=" ",
        overlay="Key Result",
        duration=3.0,
    )
    content = generator.build_ass(script_scene, duration_seconds=3.0)
    assert "KEY" in content
