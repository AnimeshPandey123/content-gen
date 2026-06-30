"""Unit tests for screenshot region planning."""

from pathlib import Path

import pytest
from app.config import Settings
from app.models.blocks import Paragraph
from app.models.bounding_box import BoundingBox
from app.models.document import Document
from app.models.metadata import DocumentMetadata
from app.models.page import Page
from app.models.pipeline import PipelineInput
from app.services.screenshot_region_planner import ScreenshotRegionError, ScreenshotRegionPlanner
from app.services.stages.content_planning import ContentPlanningStage
from app.services.stages.document_extraction import DocumentExtractionStage
from app.services.stages.semantic_parsing import SemanticParsingStage
from app.services.stages.storyboard_generation import StoryboardGenerationStage

from tests.conftest import mock_section_selection, mock_storyboard_generation, sample_scene


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


def test_crop_for_paragraph_raises_when_paragraph_has_no_bbox() -> None:
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
        planner.crop_for_paragraph(document, 1)


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


def test_crop_for_paragraph_returns_page_and_bbox() -> None:
    document = _document_with_paragraphs(3)
    planner = ScreenshotRegionPlanner(settings=Settings(screenshot_padding=0))

    page_number, crop = planner.crop_for_paragraph(document, 2)

    assert page_number == 1
    assert crop.y == 72.0 + 24.0


def test_region_for_scene_uses_storyboard_source() -> None:
    document = _document_with_paragraphs(3)
    planner = ScreenshotRegionPlanner(settings=Settings(screenshot_padding=0))
    scene = sample_scene(
        source=sample_scene().source.model_copy(update={"paragraph": 3}),
    )

    region = planner.region_for_scene(document, scene)

    assert region.paragraph_index == 3
    assert region.scene_id == scene.id


def test_storyboard_scene_visual_matches_crop_for_paragraph(
    tmp_path: Path,
    semantic_pdf: Path,
    monkeypatch,
) -> None:
    from app.config import Settings

    mock_section_selection(monkeypatch)
    mock_storyboard_generation(monkeypatch)
    settings = Settings(output_dir=tmp_path / "output", screenshot_padding=0)
    document = DocumentExtractionStage(settings=settings).run(
        PipelineInput(pdf_path=str(semantic_pdf), project_id="shot-doc"),
    )
    document = SemanticParsingStage(settings=settings).run(document)
    content_plan = ContentPlanningStage().run(document)
    storyboard_result = StoryboardGenerationStage().run(content_plan)

    scene = storyboard_result.storyboard.scenes[0]
    assert scene.visual.page >= 1
    assert scene.visual.crop.width > 0
    assert scene.visual.crop.height > 0
    assert scene.source.paragraph is not None
