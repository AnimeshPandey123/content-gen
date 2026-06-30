"""Logical content section within a document."""

from pydantic import BaseModel, Field


class Section(BaseModel):
    """A coherent block of content selected for the video."""

    id: str
    title: str
    content: str
    page_numbers: list[int] = Field(min_length=1)
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
