"""PDF text and image extraction using PyMuPDF."""

from pathlib import Path

import fitz

from app.models.document import Document
from app.models.metadata import DocumentMetadata
from app.models.page import Page


class PDFExtractionError(Exception):
    """Raised when a PDF cannot be read or processed."""


class PDFExtractor:
    """Extract structured content and page images from PDF files."""

    def __init__(self, *, output_dir: Path, image_dpi: int = 150) -> None:
        self._output_dir = output_dir
        self._image_dpi = image_dpi

    def extract(self, pdf_path: str | Path, *, document_id: str) -> Document:
        path = Path(pdf_path)
        if not path.is_file():
            raise PDFExtractionError(f"PDF file not found: {path}")

        try:
            pdf = fitz.open(path)
        except Exception as exc:
            raise PDFExtractionError(f"Failed to open PDF: {path}") from exc

        try:
            if pdf.page_count == 0:
                raise PDFExtractionError(f"PDF has no pages: {path}")

            metadata = self._extract_metadata(pdf)
            pages = self._extract_pages(pdf, document_id=document_id)
            title = pdf.metadata.get("title") or path.stem

            return Document(
                id=document_id,
                source_path=str(path.resolve()),
                title=title,
                metadata=metadata,
                pages=pages,
            )
        finally:
            pdf.close()

    def _extract_metadata(self, pdf: fitz.Document) -> DocumentMetadata:
        meta = pdf.metadata or {}
        return DocumentMetadata(
            page_count=pdf.page_count,
            author=meta.get("author") or None,
            subject=meta.get("subject") or None,
            creator=meta.get("creator") or None,
            producer=meta.get("producer") or None,
            creation_date=meta.get("creationDate") or None,
        )

    def _extract_pages(self, pdf: fitz.Document, *, document_id: str) -> list[Page]:
        pages_dir = self._output_dir / document_id / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)

        pages: list[Page] = []
        zoom = self._image_dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        for index in range(pdf.page_count):
            page = pdf[index]
            page_number = index + 1
            rect = page.rect

            image_path = pages_dir / f"page_{page_number:04d}.png"
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            pixmap.save(str(image_path))

            pages.append(
                Page(
                    page_number=page_number,
                    text=page.get_text("text").strip(),
                    width=rect.width,
                    height=rect.height,
                    image_path=str(image_path.resolve()),
                )
            )

        return pages
