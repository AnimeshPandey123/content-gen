"""Extract section candidates from a semantic document."""

from dataclasses import dataclass, field

from app.models.blocks import Heading, SemanticBlock, Table
from app.models.document import Document
from app.services.screenshot_region_planner import ScreenshotRegionPlanner


@dataclass
class SectionCandidate:
    """A document section available for LLM ranking."""

    title: str
    content: str
    page_numbers: list[int] = field(default_factory=list)
    paragraph_indices: list[int] = field(default_factory=list)


def extract_section_candidates(document: Document) -> list[SectionCandidate]:
    """Build section candidates from headings and their following content."""
    paragraph_index_by_block_id = {
        ref.block.id: ref.index for ref in ScreenshotRegionPlanner().iter_paragraphs(document)
    }
    candidates: list[SectionCandidate] = []
    current: SectionCandidate | None = None

    for page in document.pages:
        for block in page.blocks:
            current = _consume_block(
                block,
                page_number=page.page_number,
                current=current,
                candidates=candidates,
                paragraph_index_by_block_id=paragraph_index_by_block_id,
            )

    if current is not None and _has_content(current):
        candidates.append(current)

    if candidates:
        return candidates

    return [_fallback_candidate(document)]


def _consume_block(
    block: SemanticBlock,
    *,
    page_number: int,
    current: SectionCandidate | None,
    candidates: list[SectionCandidate],
    paragraph_index_by_block_id: dict[str, int],
) -> SectionCandidate | None:
    if block.type == "heading":
        if current is not None and _has_content(current):
            candidates.append(current)
        assert isinstance(block, Heading)
        return SectionCandidate(title=block.text.strip(), content="", page_numbers=[page_number])

    if block.type == "caption":
        return _append_section_text(current, page_number, block.text.strip())

    if block.type == "table":
        assert isinstance(block, Table)
        table_text = _format_table_text(block)
        if table_text:
            return _append_section_text(
                current,
                page_number,
                f"[Table]\n{table_text}",
            )
        return current

    if block.type != "paragraph":
        return current

    if current is None:
        current = SectionCandidate(
            title=f"Page {page_number}",
            content="",
            page_numbers=[page_number],
        )

    if page_number not in current.page_numbers:
        current.page_numbers.append(page_number)

    paragraph_index = paragraph_index_by_block_id.get(block.id)
    if paragraph_index and paragraph_index not in current.paragraph_indices:
        current.paragraph_indices.append(paragraph_index)

    return _append_section_text(current, page_number, block.text.strip())


def _append_section_text(
    current: SectionCandidate | None,
    page_number: int,
    text: str,
) -> SectionCandidate:
    if not text:
        return current if current is not None else SectionCandidate(
            title=f"Page {page_number}",
            content="",
            page_numbers=[page_number],
        )

    if current is None:
        current = SectionCandidate(
            title=f"Page {page_number}",
            content="",
            page_numbers=[page_number],
        )

    if page_number not in current.page_numbers:
        current.page_numbers.append(page_number)

    if current.content:
        current.content += "\n\n"
    current.content += text
    return current


def _format_table_text(block: Table) -> str:
    rows: list[str] = []
    for row in block.rows:
        line = " | ".join(cell.strip() for cell in row if cell.strip())
        if line:
            rows.append(line)
    return "\n".join(rows)


def _has_content(candidate: SectionCandidate) -> bool:
    return bool(candidate.content.strip() or candidate.title.strip())


def _fallback_candidate(document: Document) -> SectionCandidate:
    paragraph_indices = [ref.index for ref in ScreenshotRegionPlanner().iter_paragraphs(document)]
    return SectionCandidate(
        title=document.title or "Document Overview",
        content=document.raw_text[:12000],
        page_numbers=[page.page_number for page in document.pages],
        paragraph_indices=paragraph_indices[:1],
    )
