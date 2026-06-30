"""Screenshot region targeting model."""

from pydantic import BaseModel, Field


class ScreenshotRegion(BaseModel):
    """A rectangular region on a PDF page to capture as a visual."""

    scene_id: str
    page_number: int = Field(ge=1, description="1-based PDF page number")
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    paragraph_index: int | None = Field(
        default=None,
        ge=1,
        description="1-based document paragraph index (e.g. Paragraph 17)",
    )
    block_id: str | None = Field(default=None, description="Source semantic block ID")
