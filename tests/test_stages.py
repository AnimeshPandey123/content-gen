"""Unit tests for stage interface contracts."""

from app.models.blocks import Paragraph
from app.models.bounding_box import BoundingBox
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
    from app.models.storyboard_generation import PlannedScene, StoryboardGenerationResponse
    from app.services.storyboard_generator import StoryboardGenerator

    class _FakeClient:
        def generate_model(self, prompt, response_model):
            return StoryboardGenerationResponse(
                scenes=[
                    PlannedScene(
                        goal="Introduce the sample",
                        duration_seconds=5.0,
                        source="T",
                        screenshot="Opening paragraph",
                        paragraph_index=1,
                        narration="Here is the sample content.",
                        caption="Sample",
                    ),
                ],
            )

    stage = StoryboardGenerationStage(
        generator=StoryboardGenerator(gemini_client=_FakeClient()),
    )
    result = stage.run(_sample_content_plan())
    assert isinstance(result, StoryboardResult)
    scene = result.storyboard.scenes[0]
    assert scene.goal == "Introduce the sample"
    assert scene.narration == "Here is the sample content."
    assert scene.caption == "Sample"


def test_screenshot_planning_output_type() -> None:
    from app.models.storyboard_generation import PlannedScene, StoryboardGenerationResponse
    from app.services.storyboard_generator import StoryboardGenerator

    class _FakeClient:
        def generate_model(self, prompt, response_model):
            return StoryboardGenerationResponse(
                scenes=[
                    PlannedScene(
                        goal="Introduce the sample",
                        duration_seconds=5.0,
                        source="T",
                        screenshot="Opening paragraph",
                        paragraph_index=1,
                        narration="Here is the sample content.",
                        caption="Sample",
                    ),
                ],
            )

    generator = StoryboardGenerator(gemini_client=_FakeClient())
    storyboard_result = StoryboardGenerationStage(generator=generator).run(_sample_content_plan())
    result = ScreenshotPlanningStage().run(storyboard_result)
    assert isinstance(result, ScreenshotPlan)
    assert len(result.regions) >= 1
    assert result.regions[0].paragraph_index == 1
    assert result.regions[0].width > 0


def _storyboard_result_with_scenes(scenes: list) -> StoryboardResult:
    from app.models.storyboard import Storyboard

    content_plan = _sample_content_plan()
    return StoryboardResult(
        content_plan=content_plan,
        storyboard=Storyboard(document_id=content_plan.document.id, scenes=scenes),
    )


def test_narration_generation_uses_storyboard_scripts() -> None:
    from app.models.scene import Scene

    storyboard_result = _storyboard_result_with_scenes(
        [
            Scene(
                id="scene-1",
                section_id="sec-1",
                order=0,
                goal="Hook",
                duration_seconds=4.0,
                source="T",
                screenshot="Paragraph 1",
                narration="Planned narration",
                caption="Hook",
                paragraph_index=1,
            ),
        ],
    )
    screenshot_plan = ScreenshotPlanningStage().run(storyboard_result)
    result = NarrationGenerationStage().run(screenshot_plan)
    assert isinstance(result, NarrationPlan)
    assert result.narrations[0].text == "Planned narration"


def test_caption_generation_builds_timeline_from_storyboard() -> None:
    from app.models.scene import Scene

    storyboard_result = _storyboard_result_with_scenes(
        [
            Scene(
                id="scene-1",
                section_id="sec-1",
                order=0,
                goal="Hook",
                duration_seconds=4.0,
                source="T",
                screenshot="Paragraph 1",
                narration="First",
                caption="First caption",
                paragraph_index=1,
            ),
            Scene(
                id="scene-2",
                section_id="sec-1",
                order=1,
                goal="Evidence",
                duration_seconds=6.0,
                source="T",
                screenshot="Paragraph 1",
                narration="Second",
                caption="Second caption",
                paragraph_index=1,
            ),
        ],
    )
    screenshot_plan = ScreenshotPlanningStage().run(storyboard_result)
    narration_plan = NarrationGenerationStage().run(screenshot_plan)
    result = CaptionGenerationStage().run(narration_plan)
    assert isinstance(result, CaptionPlan)
    assert result.captions[0].text == "First caption"
    assert result.captions[0].start_time == 0.0
    assert result.captions[0].end_time == 4.0
    assert result.captions[1].text == "Second caption"
    assert result.captions[1].start_time == 4.0
    assert result.captions[1].end_time == 10.0


def test_narration_generation_output_type() -> None:
    from app.models.storyboard_generation import PlannedScene, StoryboardGenerationResponse
    from app.services.storyboard_generator import StoryboardGenerator

    class _FakeClient:
        def generate_model(self, prompt, response_model):
            return StoryboardGenerationResponse(
                scenes=[
                    PlannedScene(
                        goal="Introduce the sample",
                        duration_seconds=5.0,
                        source="T",
                        screenshot="Opening paragraph",
                        paragraph_index=1,
                        narration="Here is the sample content.",
                        caption="Sample",
                    ),
                ],
            )

    generator = StoryboardGenerator(gemini_client=_FakeClient())
    storyboard_result = StoryboardGenerationStage(generator=generator).run(_sample_content_plan())
    screenshot_plan = ScreenshotPlanningStage().run(storyboard_result)
    result = NarrationGenerationStage().run(screenshot_plan)
    assert isinstance(result, NarrationPlan)
    assert len(result.narrations) >= 1


def test_caption_generation_output_type() -> None:
    from app.models.storyboard_generation import PlannedScene, StoryboardGenerationResponse
    from app.services.storyboard_generator import StoryboardGenerator

    class _FakeClient:
        def generate_model(self, prompt, response_model):
            return StoryboardGenerationResponse(
                scenes=[
                    PlannedScene(
                        goal="Introduce the sample",
                        duration_seconds=5.0,
                        source="T",
                        screenshot="Opening paragraph",
                        paragraph_index=1,
                        narration="Here is the sample content.",
                        caption="Sample",
                    ),
                ],
            )

    generator = StoryboardGenerator(gemini_client=_FakeClient())
    storyboard_result = StoryboardGenerationStage(generator=generator).run(_sample_content_plan())
    screenshot_plan = ScreenshotPlanningStage().run(storyboard_result)
    narration_plan = NarrationGenerationStage().run(screenshot_plan)
    result = CaptionGenerationStage().run(narration_plan)
    assert isinstance(result, CaptionPlan)
    assert len(result.captions) >= 1


def test_video_rendering_output_type(tmp_path, monkeypatch) -> None:
    from app.models.storyboard_generation import PlannedScene, StoryboardGenerationResponse
    from app.services.storyboard_generator import StoryboardGenerator

    class _FakeClient:
        def generate_model(self, prompt, response_model):
            return StoryboardGenerationResponse(
                scenes=[
                    PlannedScene(
                        goal="Introduce the sample",
                        duration_seconds=5.0,
                        source="T",
                        screenshot="Opening paragraph",
                        paragraph_index=1,
                        narration="Here is the sample content.",
                        caption="Sample",
                    ),
                ],
            )

    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
    from app.config import reset_settings

    reset_settings()

    generator = StoryboardGenerator(gemini_client=_FakeClient())
    storyboard_result = StoryboardGenerationStage(generator=generator).run(_sample_content_plan())
    screenshot_plan = ScreenshotPlanningStage().run(storyboard_result)
    narration_plan = NarrationGenerationStage().run(screenshot_plan)
    caption_plan = CaptionGenerationStage().run(narration_plan)
    result = VideoRenderingStage().run(caption_plan)

    assert result.success is True
    assert result.project.output_path is not None
    assert str(tmp_path) in result.video_path
