"""Storyboard aggregate model."""

from pydantic import BaseModel, Field

from app.models.scene import Scene


class Storyboard(BaseModel):
    """Ordered collection of scenes derived from document content."""

    document_id: str
    scenes: list[Scene] = Field(min_length=1)
