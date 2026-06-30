"""Unit tests for stage interface contracts."""

from pathlib import Path

from app.models.blocks import Paragraph
from app.models.bounding_box import BoundingBox
from app.models.document import Document
from app.models.metadata import DocumentMetadata
from app.models.page import Page
from app.models.pipeline import ContentPlan, PipelineInput, ScriptPlan, StoryboardResult
from app.models.render import RenderProject, SceneAssets
from app.models.script_generation import GeneratedScriptScene, ScriptGenerationResponse
from app.models.section import Section
from app.models.storyboard_generation import (
    PlannedScene,
    PlannedSceneSource,
    StoryboardGenerationResponse,
)
from app.services.script_generator import ScriptGenerator
from app.services.stages.content_planning import ContentPlanningStage
from app.services.stages.document_extraction import DocumentExtractionStage
from app.services.stages.screenshot_generation import ScreenshotGenerationStage
from app.services.stages.script_generation import ScriptGenerationStage
from app.services.stages.semantic_parsing import SemanticParsingStage
from app.services.stages.storyboard_generation import StoryboardGenerationStage
from app.services.stages.subtitle_generation import SubtitleGenerationStage
from app.services.stages.video_rendering import VideoRenderingStage
from app.services.stages.voice_generation import VoiceGenerationStage
from app.services.storyboard_generator import StoryboardGenerator
from app.workflows.stage import Stage


def _sample_document() -> Document:
    return Document(
        id="doc-test",
        source_path="/tmp/test.pdf",
        metadata=DocumentMetadata(page_count=1),
        pages=[
            Page(
                page_number=1,
                text="Sample",
                width=612,
                height=792,
                blocks=[
                    Paragraph(
                        id="p1",
                        order=0,
                        text="Sample",
                        bbox=BoundingBox(x=72, y=72, width=400, height=18),
                    ),
                ],
            ),
        ],
    )


def _sample_content_plan() -> ContentPlan:
    doc = _sample_document()
    section = Section(id="sec-1", title="T", content="Sample", page_numbers=[1])
    return ContentPlan(document=doc, selected_sections=[section])


def _fake_storyboard_client():
    class _FakeClient:
        def generate_model(self, prompt, response_model):
            return StoryboardGenerationResponse(
                scenes=[
                    PlannedScene(
                        goal="Introduce the sample",
                        duration_seconds=5.0,
                        source=PlannedSceneSource(section="T", page=1, paragraph=1),
                    ),
                ],
            )

    return _FakeClient()


def _fake_script_client():
    class _FakeClient:
        def generate_model(self, prompt, response_model):
            return ScriptGenerationResponse(
                scenes=[
                    GeneratedScriptScene(
                        scene=1,
                        voice="Here is the sample content.",
                        overlay="Sample",
                        duration=5.0,
                    ),
                ],
            )

    return _FakeClient()


def test_all_stages_implement_stage_interface() -> None:
    stages = [
        DocumentExtractionStage(),
        SemanticParsingStage(),
        ContentPlanningStage(),
        StoryboardGenerationStage(),
        ScriptGenerationStage(),
        ScreenshotGenerationStage(),
        VoiceGenerationStage(),
        SubtitleGenerationStage(),
        VideoRenderingStage(),
    ]
    for stage in stages:
        assert isinstance(stage, Stage)
        assert isinstance(stage.name, str)
        assert len(stage.name) > 0


def test_document_extraction_output_type(tmp_path, sample_pdf) -> None:
    from app.config import Settings

    stage = DocumentExtractionStage(settings=Settings(output_dir=tmp_path / "output"))
    result = stage.run(PipelineInput(pdf_path=str(sample_pdf), project_id="p1"))
    assert isinstance(result, Document)
    assert result.source_path == str(sample_pdf.resolve())
    assert result.metadata.page_count == 2
    assert len(result.pages) == 2
    assert result.raw_text
    assert all(page.image_path for page in result.pages)


def test_semantic_parsing_output_type(tmp_path, sample_pdf) -> None:
    from app.config import Settings

    settings = Settings(output_dir=tmp_path / "output")
    document = DocumentExtractionStage(settings=settings).run(
        PipelineInput(pdf_path=str(sample_pdf), project_id="p1"),
    )
    result = SemanticParsingStage(settings=settings).run(document)
    assert isinstance(result, Document)
    assert all(page.blocks for page in result.pages)


def test_content_planning_output_type() -> None:
    from app.models.section_selection import RankedSection, SectionSelectionResponse
    from app.services.section_selector import SectionSelector

    class _FakeClient:
        def generate_model(self, prompt, response_model):
            return SectionSelectionResponse(
                sections=[RankedSection(section="Page 1", importance=0.9)],
            )

    stage = ContentPlanningStage(
        selector=SectionSelector(gemini_client=_FakeClient()),
    )
    result = stage.run(_sample_document())
    assert isinstance(result, ContentPlan)
    assert len(result.selected_sections) == 1
    assert result.selected_sections[0].importance_score == 0.9


def test_storyboard_generation_output_type() -> None:
    stage = StoryboardGenerationStage(
        generator=StoryboardGenerator(gemini_client=_fake_storyboard_client()),
    )
    result = stage.run(_sample_content_plan())
    assert isinstance(result, StoryboardResult)
    scene = result.storyboard.scenes[1]
    assert scene.goal == "Introduce the sample"
    assert scene.visual.crop.width > 0


def test_script_generation_output_type() -> None:
    storyboard_result = StoryboardGenerationStage(
        generator=StoryboardGenerator(gemini_client=_fake_storyboard_client()),
    ).run(_sample_content_plan())
    result = ScriptGenerationStage(
        generator=ScriptGenerator(gemini_client=_fake_script_client()),
    ).run(storyboard_result)
    assert isinstance(result, ScriptPlan)
    assert result.script.scenes[0].voice == "Here is the sample content."
    assert result.script.scenes[0].overlay == "Sample"


def test_video_rendering_output_type(tmp_path, monkeypatch) -> None:
    class _FakeAssembler:
        def render(self, project: RenderProject) -> RenderProject:
            from app.models.render import SceneClip

            video_path = Path(project.project_dir) / "final.mp4"
            video_path.parent.mkdir(parents=True, exist_ok=True)
            video_path.write_text("video", encoding="utf-8")
            clip_path = Path(project.project_dir) / "clips" / "scene01.mp4"
            clip_path.parent.mkdir(parents=True, exist_ok=True)
            clip_path.write_text("clip", encoding="utf-8")
            clips = [
                SceneClip(scene_id=project.scenes[0].scene_id, clip_path=str(clip_path)),
            ]
            return project.with_clips(clips).with_video_path(str(video_path))

    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
    from app.config import reset_settings

    reset_settings()

    storyboard_result = StoryboardGenerationStage(
        generator=StoryboardGenerator(gemini_client=_fake_storyboard_client()),
    ).run(_sample_content_plan())
    script_plan = ScriptGenerationStage(
        generator=ScriptGenerator(gemini_client=_fake_script_client()),
    ).run(storyboard_result)
    render_project = RenderProject(
        script_plan=script_plan,
        project_dir=str(tmp_path / "proj"),
        storyboard_path=str(tmp_path / "proj" / "storyboard.json"),
        scenes=[
            SceneAssets(
                scene_number=1,
                scene_id=script_plan.script.scenes[0].scene_id,
                screenshot_path=str(tmp_path / "scene01.png"),
                audio_path=str(tmp_path / "scene01.wav"),
                audio_duration_seconds=5.0,
                subtitle_path=str(tmp_path / "scene01.ass"),
            ),
        ],
    )
    result = VideoRenderingStage(assembler=_FakeAssembler()).run(render_project)

    assert result.success is True
    assert result.project.output_path is not None
    assert result.render_project.video_path is not None
    assert result.project.script.scenes[0].overlay == "Sample"
