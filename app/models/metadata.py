"""PDF document metadata model."""

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Metadata extracted from a PDF file."""

    page_count: int = Field(ge=1)
    author: str | None = None
    subject: str | None = None
    creator: str | None = None
    producer: str | None = None
    creation_date: str | None = None
