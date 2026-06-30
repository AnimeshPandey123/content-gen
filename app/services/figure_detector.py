"""Detect figures and tables with stable labels for visual planning."""

import re
from collections.abc import Iterator

from app.models.blocks import Caption, Figure
from app.models.detected_visual import DetectedVisual, VisualKind
from app.models.document import Document

FIGURE_LABEL_PATTERN = re.compile(r"^(?:figure|fig\.?)\s*(\d+)\b", re.IGNORECASE)
TABLE_LABEL_PATTERN = re.compile(r"^(?:table|tab\.?)\s*(\d+)\b", re.IGNORECASE)
VISUAL_REFERENCE_PATTERN = re.compile(
    r"^(?:figure|fig\.?|table|tab\.?)\s*(\d+)\b",
    re.IGNORECASE,
)


class FigureDetectionError(Exception):
    """Raised when a visual reference cannot be resolved."""


class FigureDetector:
    """Catalog figures and tables extracted during semantic parsing."""

    def detect_visuals(self, document: Document) -> list[DetectedVisual]:
        """Return labeled figures and tables in reading order."""
        visuals: list[DetectedVisual] = []
        auto_figure = 1
        auto_table = 1

        for page in document.pages:
            captions = {
                block.target_id: block
                for block in page.blocks
                if block.type == "caption" and block.target_id
            }

            for block in page.blocks:
                if block.type not in {"figure", "table"}:
                    continue
                if block.bbox is None:
                    continue

                caption = captions.get(block.id)
                caption_text = caption.text if isinstance(caption, Caption) else None
                label = _label_from_caption(caption_text, block.type)
                if label is None:
                    if block.type == "figure":
                        label = f"Figure {auto_figure}"
                        auto_figure += 1
                    else:
                        label = f"Table {auto_table}"
                        auto_table += 1

                image_path = block.image_path if isinstance(block, Figure) else None
                visuals.append(
                    DetectedVisual(
                        label=label,
                        kind=block.type,
                        page_number=page.page_number,
                        block_id=block.id,
                        bbox=block.bbox,
                        caption=caption_text,
                        image_path=image_path,
                    ),
                )

        return visuals

    def iter_visuals(self, document: Document) -> Iterator[DetectedVisual]:
        yield from self.detect_visuals(document)

    def get_visual(self, document: Document, label: str) -> DetectedVisual:
        normalized = normalize_visual_label(label)
        for visual in self.detect_visuals(document):
            if normalize_visual_label(visual.label) == normalized:
                return visual
        raise FigureDetectionError(f"Visual not found: {label}")

    def find_visual(self, document: Document, label: str) -> DetectedVisual | None:
        try:
            return self.get_visual(document, label)
        except FigureDetectionError:
            return None


def normalize_visual_label(label: str) -> str:
    """Normalize labels like 'fig. 2' to 'Figure 2'."""
    cleaned = re.sub(r"\s+", " ", label.strip())
    figure_match = FIGURE_LABEL_PATTERN.match(cleaned)
    if figure_match:
        return f"Figure {figure_match.group(1)}"
    table_match = TABLE_LABEL_PATTERN.match(cleaned)
    if table_match:
        return f"Table {table_match.group(1)}"
    return cleaned


def _label_from_caption(caption_text: str | None, kind: str) -> str | None:
    if not caption_text:
        return None
    lines = caption_text.strip().splitlines()
    if not lines:
        return None
    first_line = lines[0]
    if kind == "figure":
        match = FIGURE_LABEL_PATTERN.match(first_line)
        if match:
            return f"Figure {match.group(1)}"
    if kind == "table":
        match = TABLE_LABEL_PATTERN.match(first_line)
        if match:
            return f"Table {match.group(1)}"
    return None
