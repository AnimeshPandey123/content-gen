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


def _planner_settings(**overrides) -> Settings:
    values = {
        "screenshot_padding": 0,
        "screenshot_expand_factor": 1.0,
        "screenshot_mobile_crop": False,
    }
    values.update(overrides)
    return Settings(**values)


def test_region_for_paragraph_17_returns_coordinates() -> None:
    document = _document_with_paragraphs(20)
    planner = ScreenshotRegionPlanner(settings=_planner_settings())

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
    planner = ScreenshotRegionPlanner(
        settings=_planner_settings(screenshot_padding=10, screenshot_expand_factor=1.0),
    )
    region = planner.region_for_paragraph(document, 1, scene_id="scene-1")

    assert region.x == 80.0
    assert region.y == 80.0
    assert region.x + region.width <= 100.0
    assert region.y + region.height <= 100.0


def test_crop_for_paragraph_returns_page_and_bbox() -> None:
    document = _document_with_paragraphs(3)
    planner = ScreenshotRegionPlanner(settings=_planner_settings())

    page_number, crop = planner.crop_for_paragraph(document, 2)

    assert page_number == 1
    assert crop.y == 72.0 + 24.0


def test_region_for_scene_uses_storyboard_source() -> None:
    document = _document_with_paragraphs(3)
    planner = ScreenshotRegionPlanner(settings=_planner_settings())
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
    settings = Settings(
        output_dir=tmp_path / "output",
        screenshot_padding=0,
        screenshot_expand_factor=1.0,
        screenshot_mobile_crop=False,
    )
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


def test_crop_for_framing_supports_wide_focus_and_highlight() -> None:
    document = _document_with_paragraphs(1)
    planner = ScreenshotRegionPlanner(
        settings=Settings(
            screenshot_padding=0,
            screenshot_expand_factor=3.0,
            screenshot_mobile_crop=True,
            video_width=1080,
            video_height=1920,
        ),
    )

    _, wide = planner.crop_for_framing(document, page=1, paragraph=1, framing="wide")
    _, focus = planner.crop_for_framing(document, page=1, paragraph=1, framing="focus")
    _, highlight = planner.crop_for_framing(document, page=1, paragraph=1, framing="highlight")

    assert wide.width > 0 and focus.width > 0 and highlight.width > 0
    assert wide.width == pytest.approx(612.0)
    assert focus.width == pytest.approx(612.0)
    assert focus.height >= 280.0
    assert highlight.height >= 200.0


def test_crop_for_page_returns_full_page() -> None:
    document = _document_with_paragraphs(1)
    planner = ScreenshotRegionPlanner(
        settings=Settings(video_width=1080, video_height=1920, screenshot_mobile_crop=True),
    )

    crop = planner.crop_for_page(document, 1)

    assert crop.x == 0.0
    assert crop.y == 0.0
    assert crop.width == pytest.approx(612.0)
    assert crop.height == pytest.approx(792.0)


def test_expand_factor_increases_crop_size() -> None:
    document = _document_with_paragraphs(1)
    tight = ScreenshotRegionPlanner(
        settings=Settings(
            screenshot_padding=0,
            screenshot_expand_factor=1.0,
            screenshot_mobile_crop=False,
        ),
    )
    expanded = ScreenshotRegionPlanner(
        settings=Settings(
            screenshot_padding=0,
            screenshot_expand_factor=2.0,
            screenshot_mobile_crop=False,
        ),
    )

    _, tight_crop = tight.crop_for_paragraph(document, 1)
    _, wide_crop = expanded.crop_for_paragraph(document, 1)

    assert wide_crop.width > tight_crop.width
    assert wide_crop.height > tight_crop.height


def test_crop_for_page_raises_for_missing_page() -> None:
    document = _document_with_paragraphs(1)
    planner = ScreenshotRegionPlanner()

    with pytest.raises(ScreenshotRegionError, match="Page 9 not found"):
        planner.crop_for_page(document, 9)


def test_expand_bbox_clamps_to_page_edges() -> None:
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
                        text="Corner paragraph",
                        bbox=BoundingBox(x=95.0, y=95.0, width=5.0, height=5.0),
                    ),
                ],
            ),
        ],
    )
    planner = ScreenshotRegionPlanner(
        settings=Settings(
            screenshot_padding=0,
            screenshot_expand_factor=3.0,
            screenshot_mobile_crop=False,
        ),
    )

    _, crop = planner.crop_for_paragraph(document, 1)

    assert crop.x + crop.width <= 100.0
    assert crop.y + crop.height <= 100.0


def test_mobile_crop_caps_paragraph_context_height() -> None:
    document = Document(
        id="doc-1",
        source_path="/tmp/sample.pdf",
        metadata=DocumentMetadata(page_count=1),
        pages=[
            Page(
                page_number=1,
                width=612.0,
                height=792.0,
                blocks=[
                    Paragraph(
                        id="p1",
                        order=0,
                        text="Short paragraph",
                        bbox=BoundingBox(x=72.0, y=400.0, width=400.0, height=18.0),
                    ),
                ],
            ),
        ],
    )
    planner = ScreenshotRegionPlanner(
        settings=Settings(
            video_width=1080,
            video_height=1920,
            screenshot_padding=24.0,
            screenshot_expand_factor=2.0,
            screenshot_mobile_crop=True,
        ),
    )

    _, crop = planner.crop_for_paragraph(document, 1)

    assert crop.width == pytest.approx(612.0)
    assert crop.height < 792.0
    assert crop.height >= 280.0


def test_mobile_crop_uses_full_page_width() -> None:
    planner = ScreenshotRegionPlanner(
        settings=Settings(
            video_width=1080,
            video_height=1920,
            screenshot_padding=0,
            screenshot_expand_factor=1.0,
            screenshot_mobile_crop=True,
        ),
    )
    page = Page(page_number=1, width=200.0, height=400.0)

    crop = planner._fit_mobile_aspect(
        BoundingBox(x=75.0, y=100.0, width=50.0, height=200.0),
        page,
    )

    assert crop.width == 200.0
    assert crop.x == 0.0


def test_mobile_crop_clamps_width_to_page() -> None:
    planner = ScreenshotRegionPlanner(
        settings=Settings(
            video_width=1080,
            video_height=1920,
            screenshot_mobile_crop=True,
        ),
    )
    page = Page(page_number=1, width=100.0, height=500.0)

    crop = planner._fit_mobile_aspect(
        BoundingBox(x=30.0, y=100.0, width=40.0, height=200.0),
        page,
    )

    assert crop.width == 100.0
    assert crop.x == 0.0


def test_mobile_crop_enforces_minimum_height() -> None:
    planner = ScreenshotRegionPlanner(
        settings=Settings(
            video_width=1080,
            video_height=1920,
            screenshot_mobile_crop=True,
        ),
    )
    page = Page(page_number=1, width=612.0, height=792.0)
    anchor = BoundingBox(x=72.0, y=400.0, width=400.0, height=18.0)

    crop = planner._fit_mobile_aspect(
        BoundingBox(x=72.0, y=400.0, width=50.0, height=30.0),
        page,
        anchor=anchor,
        min_height=280.0,
    )

    assert crop.height == pytest.approx(280.0, rel=0.01)
    assert crop.width == pytest.approx(612.0)


def test_mobile_crop_limits_oversized_regions() -> None:
    planner = ScreenshotRegionPlanner(
        settings=Settings(
            video_width=1080,
            video_height=1920,
            screenshot_mobile_crop=True,
        ),
    )
    page = Page(page_number=1, width=612.0, height=792.0)

    crop = planner._fit_mobile_aspect(
        BoundingBox(x=72.0, y=100.0, width=500.0, height=500.0),
        page,
    )

    assert crop.height <= 792.0 * 0.85 + 0.01
    assert crop.width == pytest.approx(612.0)


def test_crop_for_visual_raises_for_missing_label() -> None:
    planner = ScreenshotRegionPlanner()
    document = Document(
        id="doc-empty",
        source_path="/tmp/empty.pdf",
        metadata=DocumentMetadata(page_count=1),
        pages=[Page(page_number=1, text="", width=612, height=792, blocks=[])],
    )

    with pytest.raises(ScreenshotRegionError, match="Visual not found"):
        planner.crop_for_visual(document, "Figure 1")


def test_figure_mobile_crop_disabled_returns_expanded_bbox() -> None:
    planner = ScreenshotRegionPlanner(
        settings=Settings(
            video_width=1080,
            video_height=1920,
            screenshot_mobile_crop=False,
        ),
    )
    page = Page(page_number=1, width=612.0, height=792.0)
    bbox = BoundingBox(x=72.0, y=150.0, width=200.0, height=100.0)

    crop = planner._finalize_figure_crop(bbox, page)

    assert crop.width >= bbox.width


def test_figure_mobile_crop_fits_vertical_aspect() -> None:
    planner = ScreenshotRegionPlanner(
        settings=Settings(
            video_width=1080,
            video_height=1920,
            screenshot_mobile_crop=True,
        ),
    )
    page = Page(page_number=1, width=612.0, height=792.0)
    anchor = BoundingBox(x=72.0, y=150.0, width=200.0, height=100.0)

    crop = planner._fit_figure_mobile_aspect(
        BoundingBox(x=72.0, y=150.0, width=220.0, height=120.0),
        page,
        anchor=anchor,
    )

    assert crop.width / crop.height == pytest.approx(9 / 16, rel=0.01)


def test_figure_mobile_crop_expands_tall_figures() -> None:
    planner = ScreenshotRegionPlanner(
        settings=Settings(
            video_width=1080,
            video_height=1920,
            screenshot_mobile_crop=True,
        ),
    )
    page = Page(page_number=1, width=612.0, height=792.0)
    anchor = BoundingBox(x=72.0, y=150.0, width=50.0, height=100.0)

    crop = planner._fit_figure_mobile_aspect(
        BoundingBox(x=72.0, y=150.0, width=50.0, height=400.0),
        page,
        anchor=anchor,
    )

    assert crop.height >= 400.0
