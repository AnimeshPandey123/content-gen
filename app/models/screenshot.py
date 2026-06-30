"""Screenshot region targeting model."""

from pydantic import BaseModel, Field, model_validator


class ScreenshotRegion(BaseModel):
    """A rectangular region on a PDF page to capture as a visual."""

    scene_id: str
    page_number: int = Field(ge=1)
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_region(self) -> "ScreenshotRegion":
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be positive")
        return self
