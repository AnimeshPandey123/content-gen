"""Transform extracted PDF pages into a semantic document model."""

import re
from dataclasses import dataclass
from pathlib import Path
from statistics import median

import fitz

from app.models.blocks import Caption, Figure, Heading, Paragraph, SemanticBlock, Table
from app.models.bounding_box import BoundingBox
from app.models.document import Document
from app.services.pdf_extractor import PDFExtractionError

CAPTION_PATTERN = re.compile(
    r"^(?:Figure|Fig\.|Table|Tab\.)\s*\d+",
    re.IGNORECASE,
)
HEADING_SIZE_RATIO = 1.15


@dataclass
class _Candidate:
    top: float
    left: float
    block: SemanticBlock


class SemanticParser:
    """Parse PDF layout into typed semantic blocks."""

    def __init__(self, *, output_dir: Path) -> None:
        self._output_dir = output_dir

    def enrich(self, document: Document) -> Document:
        path = Path(document.source_path)
        if not path.is_file():
            raise PDFExtractionError(f"PDF file not found: {path}")

        pdf = fitz.open(path)
        try:
            pages = []
            for page_model in document.pages:
                fitz_page = pdf[page_model.page_number - 1]
                blocks = self._parse_page(
                    pdf,
                    fitz_page,
                    document_id=document.id,
                    page_number=page_model.page_number,
                )
                pages.append(page_model.model_copy(update={"blocks": blocks}))
            return document.model_copy(update={"pages": pages})
        finally:
            pdf.close()

    def _parse_page(
        self,
        pdf: fitz.Document,
        page: fitz.Page,
        *,
        document_id: str,
        page_number: int,
    ) -> list[SemanticBlock]:
        candidates: list[_Candidate] = []
        table_regions: list[tuple[float, float, float, float]] = []

        table_index = 0
        try:
            tables = page.find_tables().tables
        except Exception:
            tables = []

        for table in tables:
            bbox = BoundingBox.from_rect(table.bbox)
            table_regions.append(table.bbox)
            rows = table.extract() or []
            cleaned_rows = [
                [str(cell).strip() if cell is not None else "" for cell in row]
                for row in rows
                if any(cell is not None and str(cell).strip() for cell in row)
            ]
            if not cleaned_rows:
                continue
            table_id = self._block_id(document_id, page_number, f"table-{table_index}")
            table_index += 1
            candidates.append(
                _Candidate(
                    top=bbox.y,
                    left=bbox.x,
                    block=Table(id=table_id, order=0, bbox=bbox, rows=cleaned_rows),
                )
            )

        figure_index = 0
        page_dict = page.get_text("dict", flags=fitz.TEXTFLAGS_TEXT)
        seen_image_xrefs: set[int] = set()
        for block in page_dict.get("blocks", []):
            if block.get("type") != 1:
                continue
            bbox = BoundingBox.from_rect(tuple(block["bbox"]))
            image_path = None
            xref = block.get("image")
            if isinstance(xref, int):
                seen_image_xrefs.add(xref)
                image_path = self._save_image(
                    pdf,
                    xref=xref,
                    document_id=document_id,
                    page_number=page_number,
                    figure_index=figure_index,
                )
            figure_id = self._block_id(document_id, page_number, f"figure-{figure_index}")
            figure_index += 1
            candidates.append(
                _Candidate(
                    top=bbox.y,
                    left=bbox.x,
                    block=Figure(id=figure_id, order=0, bbox=bbox, image_path=image_path),
                )
            )

        for image in page.get_images(full=True):
            xref = image[0]
            if xref in seen_image_xrefs:
                continue
            for rect in page.get_image_rects(xref):
                bbox = BoundingBox.from_rect(tuple(rect))
                image_path = self._save_image(
                    pdf,
                    xref=xref,
                    document_id=document_id,
                    page_number=page_number,
                    figure_index=figure_index,
                )
                figure_id = self._block_id(document_id, page_number, f"figure-{figure_index}")
                figure_index += 1
                seen_image_xrefs.add(xref)
                candidates.append(
                    _Candidate(
                        top=bbox.y,
                        left=bbox.x,
                        block=Figure(
                            id=figure_id,
                            order=0,
                            bbox=bbox,
                            image_path=image_path,
                        ),
                    )
                )

        text_index = 0
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            if self._overlaps_table(block["bbox"], table_regions):
                continue

            text, font_size, is_bold = self._block_text_stats(block)
            text = text.strip()
            if not text:
                continue

            bbox = BoundingBox.from_rect(tuple(block["bbox"]))
            block_id = self._block_id(document_id, page_number, f"text-{text_index}")
            text_index += 1

            if CAPTION_PATTERN.match(text):
                semantic: SemanticBlock = Caption(id=block_id, order=0, bbox=bbox, text=text)
            elif self._is_heading(text, font_size, is_bold, page):
                semantic = Heading(
                    id=block_id,
                    order=0,
                    bbox=bbox,
                    text=text,
                    level=self._heading_level(font_size, page),
                )
            else:
                semantic = Paragraph(id=block_id, order=0, bbox=bbox, text=text)

            candidates.append(_Candidate(top=bbox.y, left=bbox.x, block=semantic))

        candidates.sort(key=lambda candidate: (round(candidate.top, 1), candidate.left))
        ordered_blocks = [
            candidate.block.model_copy(update={"order": order})
            for order, candidate in enumerate(candidates)
        ]
        return self._link_captions(ordered_blocks)

    def _link_captions(self, blocks: list[SemanticBlock]) -> list[SemanticBlock]:
        figures_tables = [block for block in blocks if block.type in {"figure", "table"}]
        updated_targets: dict[str, Figure | Table] = {}
        result: list[SemanticBlock] = []

        for block in blocks:
            if block.type != "caption":
                result.append(block)
                continue

            caption = block
            assert isinstance(caption, Caption)
            target = self._nearest_target(caption, figures_tables)
            if target is None:
                result.append(caption)
                continue

            linked_caption = caption.model_copy(update={"target_id": target.id})
            result.append(linked_caption)

            if target.id not in updated_targets and isinstance(target, (Figure, Table)):
                updated_targets[target.id] = target.model_copy(
                    update={"caption_id": caption.id},
                )

        return [updated_targets.get(block.id, block) for block in result]

    def _nearest_target(
        self,
        caption: Caption,
        targets: list[SemanticBlock],
    ) -> Figure | Table | None:
        if not targets or caption.bbox is None:
            return None

        best: Figure | Table | None = None
        best_distance = float("inf")
        for target in targets:
            if target.bbox is None or not isinstance(target, (Figure, Table)):
                continue
            vertical_gap = caption.bbox.y - (target.bbox.y + target.bbox.height)
            if vertical_gap < -10:
                continue
            distance = abs(vertical_gap) + abs(caption.bbox.x - target.bbox.x)
            if distance < best_distance:
                best_distance = distance
                best = target
        return best

    def _block_text_stats(self, block: dict) -> tuple[str, float, bool]:
        sizes: list[float] = []
        bold_count = 0
        span_count = 0
        parts: list[str] = []
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                parts.append(span.get("text", ""))
                sizes.append(float(span.get("size", 0)))
                if int(span.get("flags", 0)) & 2**4:
                    bold_count += 1
                span_count += 1
        avg_size = sum(sizes) / len(sizes) if sizes else 0.0
        is_bold = span_count > 0 and bold_count / span_count >= 0.5
        return "".join(parts), avg_size, is_bold

    def _body_font_size(self, page: fitz.Page) -> float:
        sizes: list[float] = []
        page_dict = page.get_text("dict", flags=fitz.TEXTFLAGS_TEXT)
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    size = float(span.get("size", 0))
                    if size > 0:
                        sizes.append(round(size, 1))
        if not sizes:
            return 12.0
        return float(median(sizes))

    def _is_heading(self, text: str, font_size: float, is_bold: bool, page: fitz.Page) -> bool:
        if len(text) > 200 or text.count(". ") > 1:
            return False
        body_size = self._body_font_size(page)
        if font_size >= body_size * HEADING_SIZE_RATIO:
            return True
        return is_bold and len(text.split()) <= 12 and font_size >= body_size

    def _heading_level(self, font_size: float, page: fitz.Page) -> int:
        body_size = self._body_font_size(page)
        if font_size < body_size * 1.2:
            return 3
        if font_size < body_size * 1.5:
            return 2
        return 1

    def _overlaps_table(
        self,
        bbox: tuple[float, float, float, float],
        table_regions: list[tuple[float, float, float, float]],
    ) -> bool:
        rect = fitz.Rect(bbox)
        return any(rect.intersects(region) for region in table_regions)

    def _save_image(
        self,
        pdf: fitz.Document,
        *,
        xref: int,
        document_id: str,
        page_number: int,
        figure_index: int,
    ) -> str | None:
        try:
            extracted = pdf.extract_image(xref)
        except Exception:
            return None
        ext = extracted.get("ext", "png")
        figures_dir = self._output_dir / document_id / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)
        image_path = figures_dir / f"page_{page_number:04d}_fig_{figure_index:04d}.{ext}"
        image_path.write_bytes(extracted["image"])
        return str(image_path.resolve())

    @staticmethod
    def _block_id(document_id: str, page_number: int, suffix: str) -> str:
        return f"{document_id}-p{page_number}-{suffix}"
