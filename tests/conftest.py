"""Shared test fixtures."""

from pathlib import Path

import fitz
import pytest
from app.config import reset_settings


def write_sample_pdf(
    path: Path,
    *,
    pages: list[str] | None = None,
    title: str | None = None,
) -> Path:
    """Create a minimal PDF file for tests."""
    page_texts = pages or ["Hello PDF"]
    doc = fitz.open()
    if title:
        doc.set_metadata({"title": title})

    for text in page_texts:
        page = doc.new_page()
        page.insert_text((72, 72), text)

    doc.save(path)
    doc.close()
    return path


def write_semantic_pdf(path: Path) -> Path:
    """Create a PDF with headings, paragraphs, and a caption-like line."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Introduction", fontsize=18)
    page.insert_text(
        (72, 110),
        "This is the opening paragraph of the document.",
        fontsize=11,
    )
    page.insert_text((72, 150), "Figure 1: Example diagram.", fontsize=10)
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    return write_sample_pdf(
        tmp_path / "paper.pdf",
        pages=["Page one content.", "Page two content."],
        title="Sample Paper",
    )


@pytest.fixture
def semantic_pdf(tmp_path: Path) -> Path:
    return write_semantic_pdf(tmp_path / "semantic.pdf")


@pytest.fixture(autouse=True)
def _reset_settings() -> None:
    reset_settings()
    yield
    reset_settings()
