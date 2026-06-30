"""Extracted PDF document representation."""

from pydantic import BaseModel, Field, computed_field

from app.models.metadata import DocumentMetadata
from app.models.page import Page
from app.models.section import Section


class Document(BaseModel):
    """Structured representation of a source PDF."""

    id: str
    source_path: str
    title: str = ""
    metadata: DocumentMetadata
    pages: list[Page] = Field(min_length=1)
    sections: list[Section] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def raw_text(self) -> str:
        """Full document text concatenated from all pages."""
        return "\n\n".join(page.text for page in self.pages if page.text)
