"""A single page extracted from a PDF document."""

from pydantic import BaseModel, Field


class Page(BaseModel):
    """Represents one page of a PDF."""

    page_number: int = Field(ge=1, description="1-based page index")
    text: str = Field(default="", description="Extracted plain text")
    width: float | None = Field(default=None, ge=0, description="Page width in points")
    height: float | None = Field(default=None, ge=0, description="Page height in points")
