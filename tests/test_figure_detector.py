"""Unit tests for figure and table detection."""

import pytest
from app.models.blocks import Caption, Figure, Paragraph, Table
from app.models.bounding_box import BoundingBox
from app.models.document import Document
from app.models.metadata import DocumentMetadata
from app.models.page import Page
from app.services.figure_detector import FigureDetectionError, FigureDetector, normalize_visual_label
from app.services.screenshot_region_planner import ScreenshotRegionPlanner

from tests.test_stages import _sample_document


def _document_with_visuals() -> Document:
    return Document(
        id="doc-visuals",
        source_path="/tmp/visuals.pdf",
        metadata=DocumentMetadata(page_count=1),
        pages=[
            Page(
                page_number=1,
                text="Sample with visuals",
                width=612,
                height=792,
                blocks=[
                    Paragraph(
                        id="p1",
                        order=0,
                        text="Sample paragraph",
                        bbox=BoundingBox(x=72, y=72, width=400, height=18),
                    ),
                    Figure(
                        id="f1",
                        order=1,
                        bbox=BoundingBox(x=72, y=150, width=200, height=100),
                    ),
                    Caption(
                        id="c1",
                        order=2,
                        text="Figure 1: Model architecture",
                        target_id="f1",
                    ),
                    Table(
                        id="t1",
                        order=3,
                        bbox=BoundingBox(x=72, y=280, width=300, height=80),
                        rows=[["Metric", "Value"], ["Accuracy", "95%"]],
                    ),
                    Caption(
                        id="c2",
                        order=4,
                        text="Table 1: Benchmark results",
                        target_id="t1",
                    ),
                ],
            ),
        ],
    )


def test_detect_visuals_labels_figures_and_tables() -> None:
    detector = FigureDetector()
    visuals = detector.detect_visuals(_document_with_visuals())

    assert [visual.label for visual in visuals] == ["Figure 1", "Table 1"]
    assert visuals[0].kind == "figure"
    assert visuals[1].kind == "table"


def test_detect_visuals_auto_labels_when_caption_missing() -> None:
    document = Document(
        id="doc-auto",
        source_path="/tmp/auto.pdf",
        metadata=DocumentMetadata(page_count=1),
        pages=[
            Page(
                page_number=1,
                text="",
                width=612,
                height=792,
                blocks=[
                    Figure(
                        id="f1",
                        order=0,
                        bbox=BoundingBox(x=72, y=150, width=200, height=100),
                    ),
                    Table(
                        id="t1",
                        order=1,
                        bbox=BoundingBox(x=72, y=280, width=300, height=80),
                        rows=[["A", "B"]],
                    ),
                ],
            ),
        ],
    )

    labels = [visual.label for visual in FigureDetector().detect_visuals(document)]

    assert labels == ["Figure 1", "Table 1"]


def test_normalize_visual_label() -> None:
    assert normalize_visual_label("fig. 2") == "Figure 2"
    assert normalize_visual_label("Table 3") == "Table 3"
    assert normalize_visual_label("Architecture overview") == "Architecture overview"


def test_label_from_caption_returns_none_without_prefix() -> None:
    from app.services.figure_detector import _label_from_caption

    assert _label_from_caption("Overview without a label prefix", "figure") is None
    assert _label_from_caption("   ", "figure") is None


def test_get_visual_raises_for_missing_label() -> None:
    detector = FigureDetector()

    with pytest.raises(FigureDetectionError, match="Visual not found"):
        detector.get_visual(_sample_document(), "Figure 99")


def test_crop_for_visual_returns_figure_region() -> None:
    planner = ScreenshotRegionPlanner()
    page_number, crop = planner.crop_for_visual(_document_with_visuals(), "Figure 1")

    assert page_number == 1
    assert crop.width > 0
    assert crop.height > 0
    assert crop.y <= 150


def test_find_visual_returns_none_for_missing_label() -> None:
    detector = FigureDetector()
    assert detector.find_visual(_sample_document(), "Figure 1") is None


def test_iter_visuals_yields_detected_items() -> None:
    detector = FigureDetector()
    labels = [visual.label for visual in detector.iter_visuals(_document_with_visuals())]
    assert labels == ["Figure 1", "Table 1"]


def test_detect_visuals_skips_blocks_without_bbox() -> None:
    document = Document(
        id="doc-no-bbox",
        source_path="/tmp/no-bbox.pdf",
        metadata=DocumentMetadata(page_count=1),
        pages=[
            Page(
                page_number=1,
                text="",
                width=612,
                height=792,
                blocks=[
                    Figure(id="f1", order=0),
                ],
            ),
        ],
    )

    assert FigureDetector().detect_visuals(document) == []


def test_detect_visuals_includes_figure_image_path() -> None:
    visual = FigureDetector().detect_visuals(_document_with_visuals())[0]
    assert visual.image_path is None


def test_get_visual_finds_normalized_label() -> None:
    detector = FigureDetector()
    visual = detector.get_visual(_document_with_visuals(), "fig. 1")
    assert visual.label == "Figure 1"
