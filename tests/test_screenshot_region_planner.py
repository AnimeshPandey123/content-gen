"""Unit tests for screenshot region planning."""

from pathlib import Path

import pytest
from app.config import Settings
from app.models.blocks import Paragraph
from app.models.bounding_box import BoundingBox
from app.models.document import Document
from app.models.metadata import DocumentMetadata
from app.models.page import Page
from app.models.pipeline import ContentPlan, StoryboardResult
from app.models.scene import Scene
from app.models.section import Section
from app.models.storyboard import Storyboard
from app.services.screenshot_region_planner import ScreenshotRegionError, ScreenshotRegionPlanner


def _document_with_paragraphs(count: int) -> Document:
    blocks: list[Paragraph] = []
    for index in range(1, count + 1):
        blocks.append(
            Paragraph(
                id=f"p{index}",
                order=index - 1,
                text=f"Paragraph {index} body text.",
                bbox=BoundingBox(x=72.0, y=72.0 + (index - 1) * 24.0, width=400.0, height=18.0),
            ),
        )
    return Document(
        id="doc-1",
        source_path="/tmp/sample.pdf",
        metadata=DocumentMetadata(page_count=1),
        pages=[
            Page(
                page_number=1,
                text=" ".join(block.text for block in blocks),
                width=612.0,
                height=792.0,
                blocks=blocks,
            ),
        ],
    )


def test_region_for_paragraph_17_returns_coordinates() -> None:
    document = _document_with_paragraphs(20)
    planner = ScreenshotRegionPlanner(settings=Settings(screenshot_padding=0))

    region = planner.region_for_paragraph(document, 17, scene_id="scene-17")

    assert region.paragraph_index == 17
    assert region.block_id == "p17"
    assert region.page_number == 1
    assert region.x == 72.0
    assert region.y == 72.0 + 16 * 24.0
    assert region.width == 400.0
    assert region.height == 18.0


def test_get_paragraph_raises_for_missing_index() -> None:
    document = _document_with_paragraphs(3)
    planner = ScreenshotRegionPlanner()

    with pytest.raises(ScreenshotRegionError, match="Paragraph 17 not found"):
        planner.get_paragraph(document, 17)


def test_get_paragraph_raises_for_invalid_index() -> None:
    planner = ScreenshotRegionPlanner()
    document = _document_with_paragraphs(1)

    with pytest.raises(ScreenshotRegionError, match="must be >= 1"):
        planner.get_paragraph(document, 0)


def test_region_raises_when_paragraph_has_no_bbox() -> None:
    document = Document(
        id="doc-1",
        source_path="/tmp/sample.pdf",
        metadata=DocumentMetadata(page_count=1),
        pages=[
            Page(
                page_number=1,
                blocks=[Paragraph(id="p1", order=0, text="No layout data")],
            ),
        ],
    )
    planner = ScreenshotRegionPlanner()

    with pytest.raises(ScreenshotRegionError, match="no bounding box"):
        planner.region_for_paragraph(document, 1, scene_id="scene-1")


def test_padding_clamps_to_page_bounds() -> None:
    document = Document(
        id="doc-1",
        source_path="/tmp/sample.pdf",
        metadata=DocumentMetadata(page_count=1),
        pages=[
            Page(
                page_number=1,
                width=100.0,
                height=100.0,
                blocks=[
                    Paragraph(
                        id="p1",
                        order=0,
                        text="Tight paragraph",
                        bbox=BoundingBox(x=90.0, y=90.0, width=8.0, height=8.0),
                    ),
                ],
            ),
        ],
    )
    planner = ScreenshotRegionPlanner(settings=Settings(screenshot_padding=10))
    region = planner.region_for_paragraph(document, 1, scene_id="scene-1")

    assert region.x == 80.0
    assert region.y == 80.0
    assert region.x + region.width <= 100.0
    assert region.y + region.height <= 100.0


def test_plan_for_storyboard_uses_scene_paragraph_index() -> None:
    document = _document_with_paragraphs(5)
    storyboard_result = StoryboardResult(
        content_plan=ContentPlan(
            document=document,
            selected_sections=[
                Section(
                    id="sec-1",
                    title="Highlight",
                    content="Paragraph 3",
                    page_numbers=[1],
                    paragraph_indices=[3],
                ),
            ],
        ),
        storyboard=Storyboard(
            document_id="doc-1",
            scenes=[
                Scene(
                    id="scene-1",
                    section_id="sec-1",
                    order=0,
                    description="Scene",
                    duration_seconds=4.0,
                    paragraph_index=3,
                ),
            ],
        ),
    )

    regions = ScreenshotRegionPlanner(settings=Settings(screenshot_padding=0)).plan_for_storyboard(
        storyboard_result,
    )

    assert len(regions) == 1
    assert regions[0].paragraph_index == 3
    assert regions[0].scene_id == "scene-1"
    assert regions[0].y == 72.0 + 2 * 24.0


def test_plan_for_storyboard_falls_back_to_section_paragraph_index() -> None:
    document = _document_with_paragraphs(4)
    storyboard_result = StoryboardResult(
        content_plan=ContentPlan(
            document=document,
            selected_sections=[
                Section(
                    id="sec-1",
                    title="Highlight",
                    content="Paragraph 2",
                    page_numbers=[1],
                    paragraph_indices=[2],
                ),
            ],
        ),
        storyboard=Storyboard(
            document_id="doc-1",
            scenes=[
                Scene(
                    id="scene-1",
                    section_id="sec-1",
                    order=0,
                    description="Scene",
                    duration_seconds=4.0,
                ),
            ],
        ),
    )

    regions = ScreenshotRegionPlanner(settings=Settings(screenshot_padding=0)).plan_for_storyboard(
        storyboard_result,
    )
    assert regions[0].paragraph_index == 2


def test_paragraph_index_for_section_skips_unmatched_sections() -> None:
    document = _document_with_paragraphs(3)
    storyboard_result = StoryboardResult(
        content_plan=ContentPlan(
            document=document,
            selected_sections=[
                Section(
                    id="sec-1",
                    title="First",
                    content="p1",
                    page_numbers=[1],
                    paragraph_indices=[1],
                ),
                Section(
                    id="sec-2",
                    title="Second",
                    content="p2",
                    page_numbers=[1],
                    paragraph_indices=[2],
                ),
            ],
        ),
        storyboard=Storyboard(
            document_id="doc-1",
            scenes=[
                Scene(
                    id="scene-1",
                    section_id="sec-2",
                    order=0,
                    description="Scene",
                    duration_seconds=4.0,
                ),
            ],
        ),
    )
    planner = ScreenshotRegionPlanner()
    assert planner._paragraph_index_for_section(storyboard_result, "sec-2") == 2


def test_plan_for_storyboard_defaults_to_first_paragraph() -> None:
    document = _document_with_paragraphs(2)
    storyboard_result = StoryboardResult(
        content_plan=ContentPlan(
            document=document,
            selected_sections=[
                Section(
                    id="sec-1",
                    title="Highlight",
                    content="Paragraph",
                    page_numbers=[1],
                ),
            ],
        ),
        storyboard=Storyboard(
            document_id="doc-1",
            scenes=[
                Scene(
                    id="scene-1",
                    section_id="sec-1",
                    order=0,
                    description="Scene",
                    duration_seconds=4.0,
                ),
            ],
        ),
    )

    regions = ScreenshotRegionPlanner(settings=Settings(screenshot_padding=0)).plan_for_storyboard(
        storyboard_result,
    )
    assert regions[0].paragraph_index == 1


def test_screenshot_planning_stage_with_real_pdf(
    tmp_path: Path,
    semantic_pdf: Path,
    monkeypatch,
) -> None:
    from app.config import Settings
    from app.models.pipeline import PipelineInput
    from app.services.stages.content_planning import ContentPlanningStage
    from app.services.stages.document_extraction import DocumentExtractionStage
    from app.services.stages.screenshot_planning import ScreenshotPlanningStage
    from app.services.stages.semantic_parsing import SemanticParsingStage
    from app.services.stages.storyboard_generation import StoryboardGenerationStage

    from tests.conftest import mock_section_selection

    mock_section_selection(monkeypatch)
    settings = Settings(output_dir=tmp_path / "output", screenshot_padding=0)
    document = DocumentExtractionStage(settings=settings).run(
        PipelineInput(pdf_path=str(semantic_pdf), project_id="shot-doc"),
    )
    document = SemanticParsingStage(settings=settings).run(document)
    content_plan = ContentPlanningStage().run(document)
    storyboard_result = StoryboardGenerationStage().run(content_plan)
    screenshot_plan = ScreenshotPlanningStage(settings=settings).run(storyboard_result)

    region = screenshot_plan.regions[0]
    assert region.page_number >= 1
    assert region.width > 0
    assert region.height > 0
    assert region.paragraph_index is not None
    assert region.block_id is not None
