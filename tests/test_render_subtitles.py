"""Unit tests for ASS subtitle generation."""

from pathlib import Path

from app.config import Settings
from app.models.pipeline import ContentPlan, ScriptPlan, StoryboardResult
from app.models.render import SceneAudio
from app.models.script import Script, ScriptScene
from app.models.section import Section
from app.models.storyboard import Storyboard
from app.render.subtitles import SubtitleGenerator

from tests.conftest import sample_scene
from tests.test_stages import _sample_document


def _script_plan() -> ScriptPlan:
    document = _sample_document()
    return ScriptPlan(
        storyboard_result=StoryboardResult(
            content_plan=ContentPlan(
                document=document,
                selected_sections=[
                    Section(id="sec-1", title="T", content="Sample", page_numbers=[1]),
                ],
            ),
            storyboard=Storyboard(document_id=document.id, scenes=[sample_scene(id="scene-1")]),
        ),
        script=Script(
            scenes=[
                ScriptScene(
                    scene=1,
                    scene_id="scene-1",
                    voice="This paper improves accuracy",
                    overlay="Better accuracy",
                    duration=4.0,
                ),
            ],
        ),
    )


def test_build_ass_includes_karaoke_words() -> None:
    generator = SubtitleGenerator(settings=Settings())
    script_scene = _script_plan().script.scenes[0]
    content = generator.build_ass(script_scene, duration_seconds=4.0)

    assert "[Script Info]" in content
    assert "THIS" in content
    assert "PAPER" in content
    assert "\\kf" in content


def test_generate_writes_ass_files(tmp_path: Path) -> None:
    generator = SubtitleGenerator(settings=Settings(output_dir=tmp_path))
    audio_files = [SceneAudio(scene_id="scene-1", audio_path="/tmp/a.wav", duration_seconds=4.0)]
    subtitles = generator.generate(_script_plan(), audio_files)

    assert len(subtitles) == 1
    assert Path(subtitles[0].subtitle_path).exists()


def test_build_ass_falls_back_to_overlay_when_voice_empty() -> None:
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
