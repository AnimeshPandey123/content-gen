"""Extracted PDF document representation."""

from pydantic import BaseModel, Field, computed_field

from app.models.blocks import text_from_blocks
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
        """Full document text concatenated from semantic blocks or page text."""
        chunks: list[str] = []
        for page in self.pages:
            if page.blocks:
                page_text = text_from_blocks(page.blocks)
                if page_text:
                    chunks.append(page_text)
            elif page.text:
                chunks.append(page.text)
        return "\n\n".join(chunks)
