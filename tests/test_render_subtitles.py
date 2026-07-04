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
    assert "Voice" in content
    assert "\\kf" in content
    assert content.count("Dialogue:") == 1


def test_build_ass_uses_valid_ass_timestamps() -> None:
    generator = SubtitleGenerator(settings=Settings())
    script_scene = _render_project().script_plan.script.scenes[0]
    content = generator.build_ass(script_scene, duration_seconds=4.5)

    assert "0:00:04.50" in content
    assert "0:00:00.00" in content


def test_build_ass_shows_one_line_at_a_time_for_long_voice() -> None:
    from app.models.script import ScriptScene, ScriptShot

    generator = SubtitleGenerator(settings=Settings())
    script_scene = ScriptScene(
        scene=1,
        scene_id="scene-1",
        shots=[
            ScriptShot(
                shot_order=0,
                voice="one two three four five six seven eight nine ten",
                overlay="Overlay",
            ),
        ],
    )
    content = generator.build_ass(script_scene, duration_seconds=6.0)

    assert r"\N" not in content
    assert content.count("Dialogue:") == 2


def test_build_ass_emits_more_events_for_very_long_voice() -> None:
    from app.models.script import ScriptScene, ScriptShot

    generator = SubtitleGenerator(settings=Settings())
    script_scene = ScriptScene(
        scene=1,
        scene_id="scene-1",
        shots=[
            ScriptShot(
                shot_order=0,
                voice=" ".join(f"word{i}" for i in range(1, 16)),
                overlay="Overlay",
            ),
        ],
    )
    content = generator.build_ass(script_scene, duration_seconds=10.0)

    assert r"\N" not in content
    assert content.count("Dialogue:") == 3


def test_format_time_handles_subsecond_values() -> None:
    generator = SubtitleGenerator(settings=Settings())

    assert generator._format_time(1.08) == "0:00:01.08"
    assert generator._format_time(61.25) == "0:01:01.25"
    assert SubtitleGenerator(settings=Settings())._build_dialogue_events([]).startswith("Dialogue:")


def test_produce_uses_storyboard_duration_when_audio_missing(tmp_path: Path) -> None:
    project = bootstrap_render_project(
        _script_plan(),
        settings=Settings(output_dir=tmp_path),
    )
    generator = SubtitleGenerator(settings=Settings(output_dir=tmp_path))
    subtitles = generator.produce(project, [])

    content = Path(subtitles[0].subtitle_path).read_text(encoding="utf-8")
    assert "0:00:04.00" in content


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
    from app.models.script import ScriptScene, ScriptShot

    generator = SubtitleGenerator(settings=Settings())
    script_scene = ScriptScene(
        scene=1,
        scene_id="scene-1",
        shots=[
            ScriptShot(shot_order=0, voice=" ", overlay="Key Result"),
        ],
    )
    content = generator.build_ass(script_scene, duration_seconds=3.0)
    assert "Key" in content
    assert "Result" in content


def test_build_ass_falls_back_to_space_when_no_text() -> None:
    from app.models.script import ScriptScene, ScriptShot

    generator = SubtitleGenerator(settings=Settings())
    script_scene = ScriptScene(
        scene=1,
        scene_id="scene-1",
        shots=[
            ScriptShot(shot_order=0, voice=" ", overlay=" "),
        ],
    )
    content = generator.build_ass(script_scene, duration_seconds=1.0)
    assert "Dialogue:" in content
