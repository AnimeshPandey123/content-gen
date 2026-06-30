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
