"""Resolve PDF screenshot regions from semantic paragraph blocks."""

from collections.abc import Iterator
from dataclasses import dataclass

from app.config import Settings, get_settings
from app.models.blocks import Paragraph
from app.models.bounding_box import BoundingBox
from app.models.document import Document
from app.models.page import Page
from app.models.screenshot import ScreenshotRegion


class ScreenshotRegionError(Exception):
    """Raised when a screenshot region cannot be resolved."""


@dataclass(frozen=True)
class ParagraphRef:
    """A paragraph located within the document."""

    index: int
    block: Paragraph
    page_number: int
    page: Page


class ScreenshotRegionPlanner:
    """Map paragraph references to page coordinates for screenshots."""

    def __init__(self, *, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def iter_paragraphs(self, document: Document) -> Iterator[ParagraphRef]:
        """Yield paragraphs in 1-based reading order across the document."""
        index = 0
        for page in document.pages:
            for block in page.blocks:
                if block.type != "paragraph":
                    continue
                index += 1
                yield ParagraphRef(
                    index=index,
                    block=block,
                    page_number=page.page_number,
                    page=page,
                )

    def get_paragraph(self, document: Document, paragraph_index: int) -> ParagraphRef:
        if paragraph_index < 1:
            raise ScreenshotRegionError(
                f"Paragraph index must be >= 1, got {paragraph_index}",
            )

        for ref in self.iter_paragraphs(document):
            if ref.index == paragraph_index:
                return ref

        total = sum(1 for _ in self.iter_paragraphs(document))
        raise ScreenshotRegionError(
            f"Paragraph {paragraph_index} not found (document has {total} paragraph(s))",
        )

    def region_for_paragraph(
        self,
        document: Document,
        paragraph_index: int,
        *,
        scene_id: str,
    ) -> ScreenshotRegion:
        """Return page coordinates for a 1-based paragraph index."""
        ref = self.get_paragraph(document, paragraph_index)
        return self.region_from_paragraph(
            ref,
            scene_id=scene_id,
            paragraph_index=paragraph_index,
        )

    def region_from_paragraph(
        self,
        ref: ParagraphRef,
        *,
        scene_id: str,
        paragraph_index: int | None = None,
    ) -> ScreenshotRegion:
        bbox = ref.block.bbox
        if bbox is None:
            raise ScreenshotRegionError(
                f"Paragraph {ref.index} has no bounding box for screenshot planning",
            )

        padded = self._apply_padding(bbox, ref.page)
        return ScreenshotRegion(
            scene_id=scene_id,
            page_number=ref.page_number,
            x=padded.x,
            y=padded.y,
            width=padded.width,
            height=padded.height,
            paragraph_index=paragraph_index or ref.index,
            block_id=ref.block.id,
        )

    def crop_for_paragraph(
        self,
        document: Document,
        paragraph_index: int,
    ) -> tuple[int, BoundingBox]:
        """Return page number and padded crop for a paragraph."""
        ref = self.get_paragraph(document, paragraph_index)
        bbox = ref.block.bbox
        if bbox is None:
            raise ScreenshotRegionError(
                f"Paragraph {ref.index} has no bounding box for screenshot planning",
            )
        return ref.page_number, self._apply_padding(bbox, ref.page)

    def region_for_scene(self, document: Document, scene) -> ScreenshotRegion:
        """Return screenshot region derived from a storyboard scene."""
        return self.region_for_paragraph(
            document,
            scene.source.paragraph,
            scene_id=scene.id,
        )

    def _apply_padding(self, bbox: BoundingBox, page: Page) -> BoundingBox:
        padding = self._settings.screenshot_padding
        if padding <= 0:
            return bbox

        page_width = page.width or bbox.x + bbox.width + padding
        page_height = page.height or bbox.y + bbox.height + padding

        x = max(0.0, bbox.x - padding)
        y = max(0.0, bbox.y - padding)
        right = min(page_width, bbox.x + bbox.width + padding)
        bottom = min(page_height, bbox.y + bbox.height + padding)
        width = max(right - x, 1.0)
        height = max(bottom - y, 1.0)
        return BoundingBox(x=x, y=y, width=width, height=height)
