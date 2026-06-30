"""A single page extracted from a PDF document."""

from pydantic import BaseModel, Field

from app.models.blocks import SemanticBlock


class Page(BaseModel):
    """Represents one page of a PDF."""

    page_number: int = Field(ge=1, description="1-based page index")
    text: str = Field(default="", description="Extracted plain text")
    width: float | None = Field(default=None, ge=0, description="Page width in points")
    height: float | None = Field(default=None, ge=0, description="Page height in points")
    image_path: str | None = Field(default=None, description="Path to rendered page image")
    blocks: list[SemanticBlock] = Field(
        default_factory=list,
        description="Semantically typed content blocks in reading order",
    )
