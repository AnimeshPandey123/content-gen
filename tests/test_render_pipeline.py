"""Unit tests for the render pipeline orchestrator."""

from pathlib import Path

from app.config import Settings
from app.models.pipeline import ContentPlan, ScriptPlan, StoryboardResult
from app.models.render import SceneAudio, SceneScreenshot, SceneSubtitle
from app.models.script import Script, ScriptScene
from app.models.section import Section
from app.models.storyboard import Storyboard
from app.render.pipeline import RenderPipeline

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
                    voice="Voice line",
                    overlay="Overlay",
                    duration=5.0,
                ),
            ],
        ),
    )


def test_run_orchestrates_render_stages(monkeypatch, tmp_path: Path) -> None:
    class _FakeScreenshotGenerator:
        def generate(self, script_plan):
            return [SceneScreenshot(scene_id="scene-1", image_path=str(tmp_path / "s.png"))]

    class _FakeVoiceGenerator:
        def generate(self, script_plan):
            return [
                SceneAudio(
                    scene_id="scene-1",
                    audio_path=str(tmp_path / "a.wav"),
                    duration_seconds=5.0,
                ),
            ]

    class _FakeSubtitleGenerator:
        def generate(self, script_plan, audio_files):
            return [SceneSubtitle(scene_id="scene-1", subtitle_path=str(tmp_path / "s.ass"))]

    class _FakeFFmpegRenderer:
        def render_scene(self, **kwargs):
            kwargs["output_path"].write_text("clip", encoding="utf-8")

        def concat_clips(self, clip_paths, output_path):
            output_path.write_text("video", encoding="utf-8")

    pipeline = RenderPipeline(
        settings=Settings(output_dir=tmp_path),
        screenshot_generator=_FakeScreenshotGenerator(),
        voice_generator=_FakeVoiceGenerator(),
        subtitle_generator=_FakeSubtitleGenerator(),
        ffmpeg_renderer=_FakeFFmpegRenderer(),
    )

    artifacts = pipeline.run(_script_plan())

    assert artifacts.video_path.endswith(".mp4")
    assert len(artifacts.scene_clips) == 1
    assert Path(artifacts.video_path).exists()
