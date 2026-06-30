"""Unit tests for semantic document parsing."""

from pathlib import Path

import pytest
from app.config import Settings
from app.models.blocks import Caption, Heading
from app.models.pipeline import PipelineInput
from app.services.pdf_extractor import PDFExtractor
from app.services.semantic_parser import SemanticParser
from app.services.stages.document_extraction import DocumentExtractionStage
from app.services.stages.semantic_parsing import SemanticParsingStage


def _extract_and_enrich(pdf_path: Path, output_dir: Path, document_id: str = "doc-1"):
    document = PDFExtractor(output_dir=output_dir).extract(pdf_path, document_id=document_id)
    return SemanticParser(output_dir=output_dir).enrich(document)


def test_semantic_parser_adds_blocks_to_pages(tmp_path: Path, sample_pdf: Path) -> None:
    document = _extract_and_enrich(sample_pdf, tmp_path / "output")
    assert all(page.blocks for page in document.pages)
    block_types = {block.type for page in document.pages for block in page.blocks}
    assert "paragraph" in block_types


def test_semantic_parser_detects_heading(tmp_path: Path, semantic_pdf: Path) -> None:
    document = _extract_and_enrich(semantic_pdf, tmp_path / "output")
    headings = [
        block for page in document.pages for block in page.blocks if block.type == "heading"
    ]
    assert headings
    assert any(
        "Introduction" in heading.text for heading in headings if isinstance(heading, Heading)
    )


def test_semantic_parser_detects_caption(tmp_path: Path, semantic_pdf: Path) -> None:
    document = _extract_and_enrich(semantic_pdf, tmp_path / "output")
    captions = [
        block for page in document.pages for block in page.blocks if block.type == "caption"
    ]
    assert captions
    assert any("Figure 1" in caption.text for caption in captions if isinstance(caption, Caption))


def test_semantic_parser_preserves_reading_order(tmp_path: Path, semantic_pdf: Path) -> None:
    document = _extract_and_enrich(semantic_pdf, tmp_path / "output")
    orders = [block.order for page in document.pages for block in page.blocks]
    assert orders == sorted(orders)
    assert orders == list(range(len(orders)))


def test_semantic_parser_updates_raw_text(tmp_path: Path, semantic_pdf: Path) -> None:
    document = _extract_and_enrich(semantic_pdf, tmp_path / "output")
    assert "Introduction" in document.raw_text
    assert "opening paragraph" in document.raw_text


def test_semantic_parsing_stage(tmp_path: Path, sample_pdf: Path) -> None:
    settings = Settings(output_dir=tmp_path / "output")
    document = DocumentExtractionStage(settings=settings).run(
        PipelineInput(pdf_path=str(sample_pdf), project_id="stage-doc"),
    )
    enriched = SemanticParsingStage(settings=settings).run(document)
    assert enriched.id == document.id
    assert all(page.blocks for page in enriched.pages)


def test_semantic_parser_raises_for_missing_source(tmp_path: Path, sample_pdf: Path) -> None:
    document = PDFExtractor(output_dir=tmp_path / "output").extract(
        sample_pdf,
        document_id="doc-1",
    )
    document = document.model_copy(update={"source_path": str(tmp_path / "missing.pdf")})
    parser = SemanticParser(output_dir=tmp_path / "output")

    from app.services.pdf_extractor import PDFExtractionError

    with pytest.raises(PDFExtractionError, match="not found"):
        parser.enrich(document)
