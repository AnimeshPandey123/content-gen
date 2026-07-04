"""Unit tests for storyboard-driven highlight resolution."""

from app.config import Settings
from app.models.bounding_box import BoundingBox
from app.models.scene import SceneShot
from app.services.highlight_resolver import HighlightResolver

from tests.test_figure_detector import _document_with_visuals
from tests.test_stages import _sample_document


def _text_shot(**overrides) -> SceneShot:
    values = {
        "order": 0,
        "goal": "Focus on the key claim",
        "duration_seconds": 4.0,
        "page": 1,
        "paragraph": 1,
        "framing": "focus",
        "crop": BoundingBox(x=0, y=0, width=612, height=792),
        "marker_highlight": True,
    }
    values.update(overrides)
    return SceneShot(**values)


def test_resolve_returns_paragraph_bbox_when_flagged() -> None:
    document = _sample_document()
    shot = _text_shot()

    highlights = HighlightResolver().resolve(document, shot)

    assert highlights == [BoundingBox(x=72, y=72, width=400, height=18)]


def test_resolve_returns_empty_when_flag_disabled() -> None:
    document = _sample_document()
    shot = _text_shot(marker_highlight=False)

    assert HighlightResolver().resolve(document, shot) == []


def test_resolve_returns_empty_when_highlights_disabled_in_settings() -> None:
    document = _sample_document()
    shot = _text_shot()
    resolver = HighlightResolver(settings=Settings(highlight_enabled=False))

    assert resolver.resolve(document, shot) == []


def test_resolve_filters_bbox_outside_crop() -> None:
    document = _sample_document()
    shot = _text_shot(crop=BoundingBox(x=0, y=0, width=50, height=50))

    assert HighlightResolver().resolve(document, shot) == []


def test_resolve_uses_visual_bbox_for_figure_shots() -> None:
    document = _document_with_visuals()
    shot = _text_shot(
        visual="Figure 1",
        crop=BoundingBox(x=0, y=100, width=612, height=200),
    )

    highlights = HighlightResolver().resolve(document, shot)

    assert highlights == [BoundingBox(x=72, y=150, width=200, height=100)]
