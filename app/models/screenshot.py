"""Screenshot region targeting model."""

from pydantic import BaseModel, Field


class ScreenshotRegion(BaseModel):
    """A rectangular region on a PDF page to capture as a visual."""

    scene_id: str
    page_number: int = Field(ge=1)
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
