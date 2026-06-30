"""Bounding box for layout-aware document blocks."""

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Axis-aligned rectangle in PDF point coordinates."""

    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)

    @classmethod
    def from_rect(cls, rect: tuple[float, float, float, float]) -> "BoundingBox":
        x0, y0, x1, y1 = rect
        return cls(x=x0, y=y0, width=x1 - x0, height=y1 - y0)


def merge_crop_for_continuity(
    previous: BoundingBox,
    current: BoundingBox,
    *,
    page_height: float,
) -> BoundingBox:
    """Expand a crop so a follow-up shot on the same page does not clip earlier context."""
    width = max(previous.width, current.width)
    x = min(previous.x, current.x)
    y = min(previous.y, current.y)
    bottom = max(previous.y + previous.height, current.y + current.height)
    height = min(bottom - y, page_height * 0.92)

    if height >= page_height * 0.65:
        y = 0.0
        height = min(page_height * 0.92, page_height)

    y = max(0.0, min(y, page_height - height))
    return BoundingBox(x=x, y=y, width=width, height=height)
