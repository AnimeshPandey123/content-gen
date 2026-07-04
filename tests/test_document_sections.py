"""Unit tests for document section candidate extraction."""

from app.models.blocks import Figure, Heading, Paragraph
from app.models.document import Document
from app.models.metadata import DocumentMetadata
from app.models.page import Page
from app.services.document_sections import extract_section_candidates


def _document_with_headings() -> Document:
    return Document(
        id="doc-1",
        source_path="/tmp/paper.pdf",
        title="Sample Paper",
        metadata=DocumentMetadata(page_count=1),
        pages=[
            Page(
                page_number=1,
                width=612,
                height=792,
                blocks=[
                    Heading(id="h1", order=0, text="Introduction", level=1),
                    Paragraph(id="p1", order=1, text="Intro body."),
                    Heading(id="h2", order=2, text="Results", level=1),
                    Paragraph(id="p2", order=3, text="We achieved 95% accuracy."),
                    Heading(id="h3", order=4, text="References", level=1),
                    Paragraph(id="p3", order=5, text="Author et al."),
                ],
            ),
        ],
    )


def test_extract_section_candidates_from_headings() -> None:
    candidates = extract_section_candidates(_document_with_headings())
    assert [candidate.title for candidate in candidates] == [
        "Introduction",
        "Results",
        "References",
    ]
    assert candidates[1].content == "We achieved 95% accuracy."
    assert candidates[1].paragraph_indices == [2]


def test_extract_section_candidates_joins_multiple_paragraphs() -> None:
    document = Document(
        id="doc-1",
        source_path="/tmp/paper.pdf",
        title="Sample Paper",
        metadata=DocumentMetadata(page_count=1),
        pages=[
            Page(
                page_number=1,
                width=612,
                height=792,
                blocks=[
                    Heading(id="h1", order=0, text="Methods", level=1),
                    Paragraph(id="p1", order=1, text="First paragraph."),
                    Paragraph(id="p2", order=2, text="Second paragraph."),
                ],
            ),
        ],
    )
    candidates = extract_section_candidates(document)
    assert candidates[0].content == "First paragraph.\n\nSecond paragraph."


def test_extract_section_candidates_includes_captions_and_tables() -> None:
    from app.models.blocks import Caption, Table

    document = Document(
        id="doc-1",
        source_path="/tmp/paper.pdf",
        title="Sample Paper",
        metadata=DocumentMetadata(page_count=1),
        pages=[
            Page(
                page_number=1,
                width=612,
                height=792,
                blocks=[
                    Heading(id="h1", order=0, text="Results", level=1),
                    Paragraph(id="p1", order=1, text="Key finding."),
                    Caption(id="c1", order=2, text="Figure 1: Accuracy over epochs."),
                    Table(
                        id="t1",
                        order=3,
                        rows=[["Model", "AP"], ["YOLO", "63.4"], ["Fast R-CNN", "70.0"]],
                    ),
                    Paragraph(id="p2", order=4, text="As shown above."),
                ],
            ),
        ],
    )
    candidates = extract_section_candidates(document)
    assert "Figure 1: Accuracy over epochs." in candidates[0].content
    assert "[Table]" in candidates[0].content
    assert "YOLO | 63.4" in candidates[0].content
    assert candidates[0].content == (
        "Key finding.\n\n"
        "Figure 1: Accuracy over epochs.\n\n"
        "[Table]\n"
        "Model | AP\n"
        "YOLO | 63.4\n"
        "Fast R-CNN | 70.0\n\n"
        "As shown above."
    )


def test_extract_section_candidates_skips_figure_blocks() -> None:
    document = Document(
        id="doc-1",
        source_path="/tmp/paper.pdf",
        title="Sample Paper",
        metadata=DocumentMetadata(page_count=1),
        pages=[
            Page(
                page_number=1,
                width=612,
                height=792,
                blocks=[
                    Heading(id="h1", order=0, text="Results", level=1),
                    Paragraph(id="p1", order=1, text="Key finding."),
                    Figure(id="f1", order=2, alt_text="Accuracy chart"),
                    Paragraph(id="p2", order=3, text="As shown above."),
                ],
            ),
        ],
    )
    candidates = extract_section_candidates(document)
    assert candidates[0].content == "Key finding.\n\nAs shown above."


def test_extract_section_candidates_spans_multiple_pages() -> None:
    document = Document(
        id="doc-1",
        source_path="/tmp/paper.pdf",
        title="Sample Paper",
        metadata=DocumentMetadata(page_count=2),
        pages=[
            Page(
                page_number=1,
                width=612,
                height=792,
                blocks=[
                    Heading(id="h1", order=0, text="Discussion", level=1),
                    Paragraph(id="p1", order=1, text="Opening on page one."),
                ],
            ),
            Page(
                page_number=2,
                width=612,
                height=792,
                blocks=[
                    Paragraph(id="p2", order=0, text="Continued on page two."),
                ],
            ),
        ],
    )
    candidates = extract_section_candidates(document)
    assert candidates[0].page_numbers == [1, 2]
    assert "Continued on page two." in candidates[0].content


def test_extract_section_candidates_starts_with_paragraph_without_heading() -> None:
    document = Document(
        id="doc-1",
        source_path="/tmp/paper.pdf",
        title="Sample Paper",
        metadata=DocumentMetadata(page_count=1),
        pages=[
            Page(
                page_number=1,
                width=612,
                height=792,
                blocks=[Paragraph(id="p1", order=0, text="Orphan paragraph.")],
            ),
        ],
    )
    candidates = extract_section_candidates(document)
    assert candidates[0].title == "Page 1"
    assert candidates[0].content == "Orphan paragraph."


def test_extract_section_candidates_fallback_without_blocks() -> None:
    document = Document(
        id="doc-1",
        source_path="/tmp/paper.pdf",
        title="Plain Doc",
        metadata=DocumentMetadata(page_count=1),
        pages=[Page(page_number=1, text="Only plain text.")],
    )
    candidates = extract_section_candidates(document)
    assert len(candidates) == 1
    assert candidates[0].title == "Plain Doc"
    assert "Only plain text." in candidates[0].content
