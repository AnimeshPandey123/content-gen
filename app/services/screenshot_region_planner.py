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

        crop = self._finalize_crop(bbox, ref.page)
        return ScreenshotRegion(
            scene_id=scene_id,
            page_number=ref.page_number,
            x=crop.x,
            y=crop.y,
            width=crop.width,
            height=crop.height,
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
        return ref.page_number, self._finalize_crop(bbox, ref.page)

    def crop_for_page(self, document: Document, page_number: int) -> BoundingBox:
        """Return a mobile-friendly crop of an entire PDF page."""
        page = self._get_page(document, page_number)
        page_width = page.width or 612.0
        page_height = page.height or 792.0
        return self._finalize_crop(
            BoundingBox(x=0.0, y=0.0, width=page_width, height=page_height),
            page,
        )

    def region_for_scene(self, document: Document, scene) -> ScreenshotRegion:
        """Return screenshot region derived from a storyboard scene."""
        return self.region_for_paragraph(
            document,
            scene.source.paragraph,
            scene_id=scene.id,
        )

    def _get_page(self, document: Document, page_number: int) -> Page:
        for page in document.pages:
            if page.page_number == page_number:
                return page
        raise ScreenshotRegionError(f"Page {page_number} not found in document")

    def _finalize_crop(self, bbox: BoundingBox, page: Page) -> BoundingBox:
        padded = self._apply_padding(bbox, page)
        expanded = self._expand_bbox(padded, page)
        return self._fit_mobile_aspect(expanded, page)

    def _apply_padding(self, bbox: BoundingBox, page: Page) -> BoundingBox:
        padding = self._settings.screenshot_padding
        if padding <= 0:
            return bbox

        page_width, page_height = self._page_size(page, bbox)
        x = max(0.0, bbox.x - padding)
        y = max(0.0, bbox.y - padding)
        right = min(page_width, bbox.x + bbox.width + padding)
        bottom = min(page_height, bbox.y + bbox.height + padding)
        width = max(right - x, 1.0)
        height = max(bottom - y, 1.0)
        return BoundingBox(x=x, y=y, width=width, height=height)

    def _expand_bbox(self, bbox: BoundingBox, page: Page) -> BoundingBox:
        factor = self._settings.screenshot_expand_factor
        if factor <= 1.0:
            return bbox

        page_width, page_height = self._page_size(page, bbox)
        center_x = bbox.x + bbox.width / 2
        center_y = bbox.y + bbox.height / 2
        width = min(bbox.width * factor, page_width)
        height = min(bbox.height * factor, page_height)
        x = max(0.0, center_x - width / 2)
        y = max(0.0, center_y - height / 2)
        if x + width > page_width:
            x = max(0.0, page_width - width)
        if y + height > page_height:
            y = max(0.0, page_height - height)
        return BoundingBox(x=x, y=y, width=width, height=height)

    def _fit_mobile_aspect(self, bbox: BoundingBox, page: Page) -> BoundingBox:
        if not self._settings.screenshot_mobile_crop:
            return bbox

        page_width, page_height = self._page_size(page, bbox)
        target_aspect = self._settings.video_width / self._settings.video_height
        center_x = bbox.x + bbox.width / 2
        center_y = bbox.y + bbox.height / 2
        width = bbox.width
        height = bbox.height

        if width / height > target_aspect:
            height = width / target_aspect
        else:
            width = height * target_aspect

        if height > page_height:
            height = page_height
            width = height * target_aspect
        if width > page_width:
            width = page_width
            height = width / target_aspect

        x = max(0.0, min(center_x - width / 2, page_width - width))
        y = max(0.0, min(center_y - height / 2, page_height - height))
        return BoundingBox(x=x, y=y, width=width, height=height)

    def _page_size(self, page: Page, bbox: BoundingBox) -> tuple[float, float]:
        page_width = page.width or bbox.x + bbox.width
        page_height = page.height or bbox.y + bbox.height
        return page_width, page_height
