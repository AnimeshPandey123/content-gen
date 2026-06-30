"""Additional semantic parser coverage tests."""

from pathlib import Path
from types import SimpleNamespace

import fitz
from app.models.blocks import Caption, Figure, Heading, Paragraph, Table
from app.models.bounding_box import BoundingBox
from app.models.document import Document
from app.models.metadata import DocumentMetadata
from app.models.page import Page
from app.services.pdf_extractor import PDFExtractor
from app.services.semantic_parser import SemanticParser


def _parser(tmp_path: Path) -> SemanticParser:
    return SemanticParser(output_dir=tmp_path / "output")


def test_link_captions_links_figure_and_table(tmp_path: Path) -> None:
    parser = _parser(tmp_path)
    figure = Figure(
        id="f1",
        order=0,
        bbox=BoundingBox(x=0, y=0, width=100, height=80),
    )
    table = Table(
        id="t1",
        order=1,
        bbox=BoundingBox(x=0, y=100, width=100, height=60),
        rows=[["A", "B"]],
    )
    figure_caption = Caption(
        id="c1",
        order=2,
        text="Figure 1: Chart",
        bbox=BoundingBox(x=0, y=85, width=100, height=12),
    )
    table_caption = Caption(
        id="c2",
        order=3,
        text="Table 1: Values",
        bbox=BoundingBox(x=0, y=165, width=100, height=12),
    )

    linked = parser._link_captions([figure, table, figure_caption, table_caption])
    by_id = {block.id: block for block in linked}

    assert isinstance(by_id["c1"], Caption)
    assert by_id["c1"].target_id == "f1"
    assert isinstance(by_id["f1"], Figure)
    assert by_id["f1"].caption_id == "c1"
    assert isinstance(by_id["t1"], Table)
    assert by_id["t1"].caption_id == "c2"


def test_nearest_target_returns_none_without_bbox(tmp_path: Path) -> None:
    parser = _parser(tmp_path)
    caption = Caption(id="c1", order=0, text="Figure 1: X")
    target = Figure(id="f1", order=1, bbox=BoundingBox(x=0, y=0, width=10, height=10))
    assert parser._nearest_target(caption, [target]) is None


def test_nearest_target_skips_targets_below_caption(tmp_path: Path) -> None:
    parser = _parser(tmp_path)
    caption = Caption(
        id="c1",
        order=0,
        text="Figure 1: X",
        bbox=BoundingBox(x=0, y=0, width=10, height=10),
    )
    target = Figure(
        id="f1",
        order=1,
        bbox=BoundingBox(x=0, y=50, width=10, height=10),
    )
    assert parser._nearest_target(caption, [target]) is None


def test_block_text_stats_detects_bold_text(tmp_path: Path) -> None:
    parser = _parser(tmp_path)
    block = {
        "lines": [
            {
                "spans": [
                    {"text": "Bold heading", "size": 11.0, "flags": 2**4},
                ],
            },
        ],
    }
    text, size, is_bold = parser._block_text_stats(block)
    assert text == "Bold heading"
    assert size == 11.0
    assert is_bold is True


def test_body_font_size_defaults_when_page_has_no_text(tmp_path: Path) -> None:
    parser = _parser(tmp_path)
    pdf_path = tmp_path / "image-only.pdf"
    doc = fitz.open()
    page = doc.new_page()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 40, 40), 1)
    pix.clear_with(255)
    image_path = tmp_path / "pixel.png"
    pix.save(str(image_path))
    page.insert_image(fitz.Rect(72, 72, 120, 120), filename=str(image_path))
    doc.save(pdf_path)
    doc.close()

    pdf = fitz.open(pdf_path)
    try:
        assert parser._body_font_size(pdf[0]) == 12.0
    finally:
        pdf.close()


def test_is_heading_rejects_multi_sentence_paragraphs(tmp_path: Path) -> None:
    parser = _parser(tmp_path)
    pdf_path = tmp_path / "body.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Sentence one. Sentence two. Sentence three.", fontsize=11)
    doc.save(pdf_path)
    doc.close()

    pdf = fitz.open(pdf_path)
    try:
        page = pdf[0]
        assert (
            parser._is_heading(
                "Sentence one. Sentence two. Sentence three.",
                11.0,
                False,
                page,
            )
            is False
        )
    finally:
        pdf.close()


def test_heading_level_tiers(tmp_path: Path) -> None:
    parser = _parser(tmp_path)
    pdf_path = tmp_path / "levels.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Body", fontsize=11)
    doc.save(pdf_path)
    doc.close()

    pdf = fitz.open(pdf_path)
    try:
        page = pdf[0]
        assert parser._heading_level(11.0, page) == 3
        assert parser._heading_level(14.0, page) == 2
        assert parser._heading_level(20.0, page) == 1
    finally:
        pdf.close()


def test_overlaps_table_detects_intersection(tmp_path: Path) -> None:
    parser = _parser(tmp_path)
    bbox = (80, 80, 120, 120)
    regions = [(70, 70, 130, 130)]
    assert parser._overlaps_table(bbox, regions) is True
    assert parser._overlaps_table((200, 200, 220, 220), regions) is False


def test_save_image_writes_file(tmp_path: Path) -> None:
    parser = _parser(tmp_path)
    pdf = fitz.open()
    page = pdf.new_page()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 20, 20), 1)
    pix.clear_with(0)
    image_path = tmp_path / "source.png"
    pix.save(str(image_path))
    page.insert_image(fitz.Rect(72, 72, 120, 120), filename=str(image_path))
    doc_path = tmp_path / "with-image.pdf"
    pdf.save(doc_path)
    pdf.close()

    pdf = fitz.open(doc_path)
    try:
        page = pdf[0]
        xref = page.get_images(full=True)[0][0]
        saved = parser._save_image(
            pdf,
            xref=xref,
            document_id="doc-1",
            page_number=1,
            figure_index=0,
        )
        assert saved is not None
        assert Path(saved).is_file()
    finally:
        pdf.close()


def test_save_image_returns_none_on_failure(tmp_path: Path, monkeypatch) -> None:
    parser = _parser(tmp_path)

    def boom(_pdf, xref):
        raise RuntimeError("extract failed")

    monkeypatch.setattr(fitz.Document, "extract_image", boom)
    assert (
        parser._save_image(
            fitz.open(),
            xref=1,
            document_id="doc-1",
            page_number=1,
            figure_index=0,
        )
        is None
    )


def test_parse_page_extracts_tables_and_skips_empty_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:
    parser = _parser(tmp_path)
    pdf = fitz.open()
    page = pdf.new_page()

    class _Table:
        def __init__(self, bbox: tuple[float, float, float, float], rows):
            self.bbox = bbox
            self._rows = rows

        def extract(self):
            return self._rows

    class _Finder:
        def __init__(self, tables):
            self.tables = tables

    tables = [
        _Table((72, 200, 300, 280), [["Metric", "Value"], ["Accuracy", "95%"]]),
        _Table((72, 300, 300, 360), [[None, None]]),
    ]
    monkeypatch.setattr(fitz.Page, "find_tables", lambda _self: _Finder(tables))
    monkeypatch.setattr(
        fitz.Page,
        "get_text",
        lambda _self, *_args, **_kwargs: {
            "blocks": [
                {
                    "type": 0,
                    "bbox": (72, 210, 200, 230),
                    "lines": [{"spans": [{"text": "inside table", "size": 11, "flags": 0}]}],
                },
                {
                    "type": 0,
                    "bbox": (72, 400, 300, 420),
                    "lines": [{"spans": [{"text": "Outside paragraph.", "size": 11, "flags": 0}]}],
                },
                {"type": 0, "bbox": (72, 440, 100, 450), "lines": [{"spans": []}]},
            ],
        },
    )

    blocks = parser._parse_page(pdf, page, document_id="doc-1", page_number=1)
    types = [block.type for block in blocks]
    assert "table" in types
    assert "paragraph" in types
    assert "inside table" not in {block.text for block in blocks if isinstance(block, Paragraph)}


def test_parse_page_handles_find_tables_failure(tmp_path: Path, monkeypatch) -> None:
    parser = _parser(tmp_path)
    pdf = fitz.open()
    page = pdf.new_page()

    def boom(_self):
        raise RuntimeError("table finder unavailable")

    monkeypatch.setattr(fitz.Page, "find_tables", boom)
    monkeypatch.setattr(
        fitz.Page,
        "get_text",
        lambda _self, *_args, **_kwargs: {
            "blocks": [
                {
                    "type": 0,
                    "bbox": (72, 72, 300, 90),
                    "lines": [{"spans": [{"text": "Fallback paragraph.", "size": 11, "flags": 0}]}],
                },
            ],
        },
    )

    blocks = parser._parse_page(pdf, page, document_id="doc-1", page_number=1)
    assert any(isinstance(block, Paragraph) for block in blocks)


def test_parse_page_extracts_figure_block(tmp_path: Path, monkeypatch) -> None:
    parser = _parser(tmp_path)
    pdf = fitz.open()
    page = pdf.new_page()

    monkeypatch.setattr(fitz.Page, "find_tables", lambda _self: SimpleNamespace(tables=[]))
    monkeypatch.setattr(
        fitz.Page,
        "get_text",
        lambda _self, *_args, **_kwargs: {
            "blocks": [
                {"type": 1, "bbox": (72, 72, 172, 172), "image": 42},
            ],
        },
    )
    monkeypatch.setattr(
        fitz.Document,
        "extract_image",
        lambda _self, xref: {"ext": "png", "image": b"png-bytes"},
    )

    blocks = parser._parse_page(pdf, page, document_id="doc-1", page_number=1)
    assert len(blocks) == 1
    assert isinstance(blocks[0], Figure)
    assert blocks[0].image_path is not None


def test_parse_page_detects_bold_heading(tmp_path: Path, monkeypatch) -> None:
    parser = _parser(tmp_path)
    pdf = fitz.open()
    page = pdf.new_page()

    monkeypatch.setattr(fitz.Page, "find_tables", lambda _self: SimpleNamespace(tables=[]))
    monkeypatch.setattr(
        fitz.Page,
        "get_text",
        lambda _self, *_args, **_kwargs: {
            "blocks": [
                {
                    "type": 0,
                    "bbox": (72, 72, 200, 90),
                    "lines": [{"spans": [{"text": "Bold Section", "size": 11, "flags": 16}]}],
                },
                {
                    "type": 0,
                    "bbox": (72, 100, 300, 120),
                    "lines": [{"spans": [{"text": "Body text.", "size": 11, "flags": 0}]}],
                },
            ],
        },
    )

    blocks = parser._parse_page(pdf, page, document_id="doc-1", page_number=1)
    assert any(isinstance(block, Heading) and block.text == "Bold Section" for block in blocks)


def test_nearest_target_skips_targets_without_bbox(tmp_path: Path) -> None:
    parser = _parser(tmp_path)
    caption = Caption(
        id="c1",
        order=0,
        text="Figure 1: X",
        bbox=BoundingBox(x=0, y=100, width=10, height=10),
    )
    target = Figure(id="f1", order=1)
    assert parser._nearest_target(caption, [target]) is None


def test_body_font_size_skips_non_text_blocks(tmp_path: Path, monkeypatch) -> None:
    parser = _parser(tmp_path)
    pdf = fitz.open()
    page = pdf.new_page()

    monkeypatch.setattr(
        fitz.Page,
        "get_text",
        lambda _self, *_args, **_kwargs: {
            "blocks": [
                {"type": 1, "bbox": (0, 0, 10, 10)},
                {
                    "type": 0,
                    "lines": [{"spans": [{"text": "Body", "size": 11.0}]}],
                },
            ],
        },
    )

    assert parser._body_font_size(page) == 11.0


def test_heading_level_tier_two(tmp_path: Path) -> None:
    parser = _parser(tmp_path)
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Body", fontsize=11)
    pdf_path = tmp_path / "tier-two.pdf"
    pdf.save(pdf_path)
    pdf.close()

    pdf = fitz.open(pdf_path)
    try:
        assert parser._heading_level(14.0, pdf[0]) == 2
    finally:
        pdf.close()


def test_parse_page_skips_duplicate_image_xrefs(tmp_path: Path, monkeypatch) -> None:
    parser = _parser(tmp_path)
    pdf = fitz.open()
    page = pdf.new_page()

    monkeypatch.setattr(fitz.Page, "find_tables", lambda _self: SimpleNamespace(tables=[]))
    monkeypatch.setattr(
        fitz.Page,
        "get_text",
        lambda _self, *_args, **_kwargs: {
            "blocks": [{"type": 1, "bbox": (72, 72, 172, 172), "image": 7}],
        },
    )
    monkeypatch.setattr(fitz.Page, "get_images", lambda _self, full=True: [(7,)])
    monkeypatch.setattr(
        fitz.Document,
        "extract_image",
        lambda _self, xref: {"ext": "png", "image": b"png-bytes"},
    )

    blocks = parser._parse_page(pdf, page, document_id="doc-1", page_number=1)
    assert len([block for block in blocks if block.type == "figure"]) == 1


def test_enrich_with_figure_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "figure.pdf"
    doc = fitz.open()
    page = doc.new_page()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 40, 40), 1)
    pix.clear_with(255)
    image_path = tmp_path / "fig.png"
    pix.save(str(image_path))
    page.insert_image(fitz.Rect(72, 72, 172, 172), filename=str(image_path))
    page.insert_text((72, 190), "Figure 1: Overview.", fontsize=10)
    doc.save(pdf_path)
    doc.close()

    document = PDFExtractor(output_dir=tmp_path / "output").extract(pdf_path, document_id="doc-1")
    enriched = SemanticParser(output_dir=tmp_path / "output").enrich(document)
    block_types = {block.type for block in enriched.pages[0].blocks}
    assert "figure" in block_types
    assert "caption" in block_types


def test_document_raw_text_falls_back_to_page_text() -> None:
    document = Document(
        id="doc-1",
        source_path="/tmp/a.pdf",
        metadata=DocumentMetadata(page_count=1),
        pages=[Page(page_number=1, text="Plain page text")],
    )
    assert document.raw_text == "Plain page text"
