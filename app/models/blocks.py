"""Semantic content blocks extracted from PDF pages."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.models.bounding_box import BoundingBox

BlockType = Literal["paragraph", "heading", "figure", "table", "caption"]


class BlockBase(BaseModel):
    """Shared fields for all semantic document blocks."""

    id: str
    order: int = Field(ge=0)
    bbox: BoundingBox | None = None


class Paragraph(BlockBase):
    """Body text block."""

    type: Literal["paragraph"] = "paragraph"
    text: str = Field(min_length=1)


class Heading(BlockBase):
    """Section heading detected by typography or structure."""

    type: Literal["heading"] = "heading"
    text: str = Field(min_length=1)
    level: int = Field(ge=1, le=6, description="Heading depth (1 = top-level)")


class Figure(BlockBase):
    """Image or diagram embedded in the page."""

    type: Literal["figure"] = "figure"
    image_path: str | None = None
    alt_text: str = ""
    caption_id: str | None = None


class Table(BlockBase):
    """Tabular data region."""

    type: Literal["table"] = "table"
    rows: list[list[str]] = Field(min_length=1)
    caption_id: str | None = None


class Caption(BlockBase):
    """Caption for a figure or table."""

    type: Literal["caption"] = "caption"
    text: str = Field(min_length=1)
    target_id: str | None = Field(
        default=None,
        description="ID of the figure or table this caption describes",
    )


SemanticBlock = Annotated[
    Paragraph | Heading | Figure | Table | Caption,
    Field(discriminator="type"),
]


def text_from_blocks(blocks: list[SemanticBlock]) -> str:
    """Concatenate human-readable text from semantic blocks."""
    parts: list[str] = []
    for block in blocks:
        if block.type in {"paragraph", "heading", "caption"}:
            parts.append(block.text)
        elif block.type == "table":
            for row in block.rows:
                parts.append(" | ".join(cell.strip() for cell in row if cell))
        elif block.type == "figure" and block.alt_text:
            parts.append(block.alt_text)
    return "\n".join(part for part in parts if part)
