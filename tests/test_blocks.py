"""Unit tests for semantic block models."""

import json

import pytest
from app.models.blocks import (
    Caption,
    Figure,
    Heading,
    Paragraph,
    Table,
    text_from_blocks,
)
from app.models.bounding_box import BoundingBox
from pydantic import TypeAdapter, ValidationError

SemanticBlockAdapter = TypeAdapter(
    Paragraph | Heading | Figure | Table | Caption,
)


def test_paragraph_requires_text() -> None:
    with pytest.raises(ValidationError):
        Paragraph(id="p1", order=0, text="")


def test_heading_level_bounds() -> None:
    with pytest.raises(ValidationError):
        Heading(id="h1", order=0, text="Title", level=0)


def test_table_requires_rows() -> None:
    with pytest.raises(ValidationError):
        Table(id="t1", order=0, rows=[])


def test_discriminated_union_round_trip() -> None:
    blocks = [
        Heading(id="h1", order=0, text="Intro", level=1),
        Paragraph(id="p1", order=1, text="Body copy."),
        Figure(id="f1", order=2, image_path="/tmp/fig.png"),
        Table(id="t1", order=3, rows=[["A", "B"], ["1", "2"]]),
        Caption(id="c1", order=4, text="Figure 1: Example", target_id="f1"),
    ]
    payload = [block.model_dump() for block in blocks]
    restored = [SemanticBlockAdapter.validate_python(item) for item in payload]
    assert [block.type for block in restored] == [
        "heading",
        "paragraph",
        "figure",
        "table",
        "caption",
    ]


def test_text_from_blocks_joins_content() -> None:
    blocks = [
        Heading(id="h1", order=0, text="Results", level=2),
        Paragraph(id="p1", order=1, text="We found a signal."),
        Table(id="t1", order=2, rows=[["Metric", "Value"], ["Accuracy", "95%"]]),
        Caption(id="c1", order=3, text="Table 1: Metrics"),
        Figure(id="f2", order=4, alt_text="Diagram"),
    ]
    text = text_from_blocks(blocks)
    assert "Results" in text
    assert "We found a signal." in text
    assert "Metric | Value" in text
    assert "Table 1: Metrics" in text
    assert "Diagram" in text


def test_blocks_serialize_to_json() -> None:
    block = Paragraph(
        id="p1",
        order=0,
        text="Hello",
        bbox=BoundingBox(x=0, y=0, width=100, height=20),
    )
    payload = json.loads(block.model_dump_json())
    assert payload["type"] == "paragraph"
    assert payload["bbox"]["width"] == 100
