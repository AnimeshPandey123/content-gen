"""Extracted PDF document representation."""

from pydantic import BaseModel, Field

from app.models.page import Page
from app.models.section import Section


class Document(BaseModel):
    """Structured representation of a source PDF."""

    id: str
    source_path: str
    title: str = ""
    pages: list[Page] = Field(min_length=1)
    sections: list[Section] = Field(default_factory=list)
