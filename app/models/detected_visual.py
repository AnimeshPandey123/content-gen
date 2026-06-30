"""Detected figures and tables available for visual planning."""

from typing import Literal

from pydantic import BaseModel, Field

from app.models.bounding_box import BoundingBox

VisualKind = Literal["figure", "table"]


class DetectedVisual(BaseModel):
    """A figure or table detected in the document with a human-readable label."""

    label: str = Field(min_length=1, description='Label such as "Figure 1" or "Table 2"')
    kind: VisualKind
    page_number: int = Field(ge=1)
    block_id: str = Field(min_length=1)
    bbox: BoundingBox
    caption: str | None = None
    image_path: str | None = None
