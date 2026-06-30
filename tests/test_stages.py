"""Unit tests for stage interface contracts."""

from app.models.document import Document
from app.models.metadata import DocumentMetadata
from app.models.page import Page
from app.models.pipeline import (
    CaptionPlan,
    ContentPlan,
    NarrationPlan,
    PipelineInput,
    ScreenshotPlan,
    StoryboardResult,
)
from app.models.section import Section
from app.services.stages.caption_generation import CaptionGenerationStage
from app.services.stages.content_planning import ContentPlanningStage
from app.services.stages.document_extraction import DocumentExtractionStage
from app.services.stages.narration_generation import NarrationGenerationStage
from app.services.stages.screenshot_planning import ScreenshotPlanningStage
from app.services.stages.semantic_parsing import SemanticParsingStage
from app.services.stages.storyboard_generation import StoryboardGenerationStage
from app.services.stages.video_rendering import VideoRenderingStage
from app.workflows.stage import Stage


def _sample_document() -> Document:
    return Document(
        id="doc-test",
        source_path="/tmp/test.pdf",
        metadata=DocumentMetadata(page_count=1),
        pages=[Page(page_number=1, text="Sample", width=612, height=792)],
    )


def _sample_content_plan() -> ContentPlan:
    doc = _sample_document()
    section = Section(id="sec-1", title="T", content="Sample", page_numbers=[1])
    return ContentPlan(document=doc, selected_sections=[section])


def test_all_stages_implement_stage_interface() -> None:
    stages = [
        DocumentExtractionStage(),
        SemanticParsingStage(),
        ContentPlanningStage(),
        StoryboardGenerationStage(),
        ScreenshotPlanningStage(),
        NarrationGenerationStage(),
        CaptionGenerationStage(),
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
    stage = ContentPlanningStage()
    result = stage.run(_sample_document())
    assert isinstance(result, ContentPlan)
    assert len(result.selected_sections) >= 1


def test_storyboard_generation_output_type() -> None:
    stage = StoryboardGenerationStage()
    result = stage.run(_sample_content_plan())
    assert isinstance(result, StoryboardResult)
    assert len(result.storyboard.scenes) >= 1


def test_screenshot_planning_output_type() -> None:
    storyboard_stage = StoryboardGenerationStage()
    storyboard_result = storyboard_stage.run(_sample_content_plan())
    result = ScreenshotPlanningStage().run(storyboard_result)
    assert isinstance(result, ScreenshotPlan)
    assert len(result.regions) >= 1


def test_narration_generation_output_type() -> None:
    storyboard_result = StoryboardGenerationStage().run(_sample_content_plan())
    screenshot_plan = ScreenshotPlanningStage().run(storyboard_result)
    result = NarrationGenerationStage().run(screenshot_plan)
    assert isinstance(result, NarrationPlan)
    assert len(result.narrations) >= 1


def test_caption_generation_output_type() -> None:
    storyboard_result = StoryboardGenerationStage().run(_sample_content_plan())
    screenshot_plan = ScreenshotPlanningStage().run(storyboard_result)
    narration_plan = NarrationGenerationStage().run(screenshot_plan)
    result = CaptionGenerationStage().run(narration_plan)
    assert isinstance(result, CaptionPlan)
    assert len(result.captions) >= 1


def test_video_rendering_output_type(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
    from app.config import reset_settings

    reset_settings()

    storyboard_result = StoryboardGenerationStage().run(_sample_content_plan())
    screenshot_plan = ScreenshotPlanningStage().run(storyboard_result)
    narration_plan = NarrationGenerationStage().run(screenshot_plan)
    caption_plan = CaptionGenerationStage().run(narration_plan)
    result = VideoRenderingStage().run(caption_plan)

    assert result.success is True
    assert result.project.output_path is not None
    assert str(tmp_path) in result.video_path
