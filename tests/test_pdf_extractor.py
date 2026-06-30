"""Unit tests for PDF extraction service."""

from pathlib import Path

import pytest
from app.models.metadata import DocumentMetadata
from app.services.pdf_extractor import PDFExtractionError, PDFExtractor

from tests.conftest import write_sample_pdf


def test_extract_reads_pdf_text(tmp_path: Path, sample_pdf: Path) -> None:
    extractor = PDFExtractor(output_dir=tmp_path / "output")
    document = extractor.extract(sample_pdf, document_id="doc-1")

    assert document.id == "doc-1"
    assert document.metadata.page_count == 2
    assert len(document.pages) == 2
    assert "Page one content." in document.pages[0].text
    assert "Page two content." in document.pages[1].text
    assert "Page one content." in document.raw_text
    assert "Page two content." in document.raw_text


def test_extract_sets_metadata(tmp_path: Path, sample_pdf: Path) -> None:
    extractor = PDFExtractor(output_dir=tmp_path / "output")
    document = extractor.extract(sample_pdf, document_id="doc-1")

    assert isinstance(document.metadata, DocumentMetadata)
    assert document.metadata.page_count == 2
    assert document.title == "Sample Paper"


def test_extract_renders_page_images(tmp_path: Path, sample_pdf: Path) -> None:
    output_dir = tmp_path / "output"
    extractor = PDFExtractor(output_dir=output_dir, image_dpi=72)
    document = extractor.extract(sample_pdf, document_id="doc-1")

    for page in document.pages:
        assert page.image_path is not None
        image_path = Path(page.image_path)
        assert image_path.is_file()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    assert (output_dir / "doc-1" / "pages" / "page_0001.png").is_file()
    assert (output_dir / "doc-1" / "pages" / "page_0002.png").is_file()


def test_extract_records_page_dimensions(tmp_path: Path) -> None:
    pdf_path = write_sample_pdf(tmp_path / "sized.pdf", pages=["Sized page"])
    extractor = PDFExtractor(output_dir=tmp_path / "output")
    document = extractor.extract(pdf_path, document_id="doc-1")

    page = document.pages[0]
    assert page.width is not None and page.width > 0
    assert page.height is not None and page.height > 0


def test_extract_raises_for_missing_file(tmp_path: Path) -> None:
    extractor = PDFExtractor(output_dir=tmp_path / "output")

    with pytest.raises(PDFExtractionError, match="not found"):
        extractor.extract(tmp_path / "missing.pdf", document_id="doc-1")


def test_extract_raises_for_invalid_pdf(tmp_path: Path) -> None:
    bad_pdf = tmp_path / "bad.pdf"
    bad_pdf.write_text("not a pdf")
    extractor = PDFExtractor(output_dir=tmp_path / "output")

    with pytest.raises(PDFExtractionError, match="Failed to open PDF"):
        extractor.extract(bad_pdf, document_id="doc-1")


def test_extract_raises_for_zero_page_pdf(tmp_path: Path, monkeypatch) -> None:
    pdf_path = write_sample_pdf(tmp_path / "normal.pdf", pages=["One page"])

    class _EmptyPDF:
        page_count = 0
        metadata: dict[str, str] = {}

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        "app.services.pdf_extractor.fitz.open",
        lambda _path: _EmptyPDF(),
    )
    extractor = PDFExtractor(output_dir=tmp_path / "output")

    with pytest.raises(PDFExtractionError, match="no pages"):
        extractor.extract(pdf_path, document_id="doc-1")
