"""Resolve PDF screenshot regions from semantic paragraph blocks."""

from collections.abc import Iterator
from dataclasses import dataclass

from app.config import Settings, get_settings
from app.models.blocks import Paragraph
from app.models.bounding_box import BoundingBox
from app.models.document import Document
from app.models.page import Page
from app.models.screenshot import ScreenshotRegion
from app.services.figure_detector import FigureDetectionError, FigureDetector


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

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        figure_detector: FigureDetector | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._figure_detector = figure_detector or FigureDetector()

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
        return self._crop_for_paragraph_index(
            document,
            paragraph_index,
            min_height=self._settings.screenshot_focus_min_height,
        )

    def crop_for_framing(
        self,
        document: Document,
        *,
        page: int,
        paragraph: int,
        framing: str,
    ) -> tuple[int, BoundingBox]:
        """Return a crop tuned to the requested camera framing."""
        if framing == "wide":
            return page, self.crop_for_page(document, page)

        if framing == "highlight":
            return self._crop_for_paragraph_index(
                document,
                paragraph,
                expand_factor=self._settings.screenshot_highlight_expand_factor,
                min_height=self._settings.screenshot_highlight_min_height,
            )

        return self._crop_for_paragraph_index(
            document,
            paragraph,
            expand_factor=self._settings.screenshot_expand_factor,
            min_height=self._settings.screenshot_focus_min_height,
        )

    def _crop_for_paragraph_index(
        self,
        document: Document,
        paragraph_index: int,
        *,
        expand_factor: float | None = None,
        padding: float | None = None,
        min_height: float | None = None,
    ) -> tuple[int, BoundingBox]:
        ref = self.get_paragraph(document, paragraph_index)
        bbox = ref.block.bbox
        if bbox is None:
            raise ScreenshotRegionError(
                f"Paragraph {ref.index} has no bounding box for screenshot planning",
            )
        return ref.page_number, self._finalize_crop(
            bbox,
            ref.page,
            anchor=bbox,
            expand_factor=expand_factor,
            padding=padding,
            min_height=min_height,
        )

    def crop_for_visual(self, document: Document, label: str) -> tuple[int, BoundingBox]:
        """Return page number and crop region for a detected figure or table."""
        try:
            visual = self._figure_detector.get_visual(document, label)
        except FigureDetectionError as exc:
            raise ScreenshotRegionError(str(exc)) from exc

        page = self._get_page(document, visual.page_number)
        return visual.page_number, self._finalize_figure_crop(visual.bbox, page)

    def crop_for_page(self, document: Document, page_number: int) -> BoundingBox:
        """Return the full PDF page so text is not clipped at the margins."""
        page = self._get_page(document, page_number)
        page_width, page_height = self._page_size(
            page,
            BoundingBox(x=0.0, y=0.0, width=612.0, height=792.0),
        )
        return BoundingBox(x=0.0, y=0.0, width=page_width, height=page_height)

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

    def _finalize_crop(
        self,
        bbox: BoundingBox,
        page: Page,
        *,
        anchor: BoundingBox | None = None,
        expand_factor: float | None = None,
        padding: float | None = None,
        min_height: float | None = None,
    ) -> BoundingBox:
        padded = self._apply_padding(bbox, page, padding=padding)
        expanded = self._expand_bbox(padded, page, expand_factor=expand_factor)
        return self._fit_mobile_aspect(
            expanded,
            page,
            anchor=anchor or bbox,
            min_height=min_height,
        )

    def _apply_padding(
        self,
        bbox: BoundingBox,
        page: Page,
        *,
        padding: float | None = None,
    ) -> BoundingBox:
        padding = self._settings.screenshot_padding if padding is None else padding
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

    def _expand_bbox(
        self,
        bbox: BoundingBox,
        page: Page,
        *,
        expand_factor: float | None = None,
    ) -> BoundingBox:
        factor = self._settings.screenshot_expand_factor if expand_factor is None else expand_factor
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

    def _finalize_figure_crop(self, bbox: BoundingBox, page: Page) -> BoundingBox:
        padded = self._apply_padding(bbox, page)
        expanded = self._expand_bbox(
            padded,
            page,
            expand_factor=self._settings.screenshot_highlight_expand_factor,
        )
        return self._fit_figure_mobile_aspect(expanded, page, anchor=bbox)

    def _fit_figure_mobile_aspect(
        self,
        bbox: BoundingBox,
        page: Page,
        *,
        anchor: BoundingBox,
    ) -> BoundingBox:
        """Frame a figure or table in a 9:16 crop centered on the visual."""
        if not self._settings.screenshot_mobile_crop:
            return bbox

        page_width, page_height = self._page_size(page, bbox)
        target_ratio = 9 / 16
        center_x = anchor.x + anchor.width / 2
        center_y = anchor.y + anchor.height / 2

        width = max(bbox.width, anchor.width * 1.2)
        height = width / target_ratio
        if height < bbox.height:
            height = bbox.height
            width = height * target_ratio

        width = min(width, page_width)
        height = min(height, page_height * 0.92)

        if height >= page_height * 0.65:
            y = 0.0
            height = min(page_height * 0.92, page_height)
            x = 0.0
            width = page_width
        else:
            x = max(0.0, min(center_x - width / 2, page_width - width))
            y = max(0.0, min(center_y - height / 2, page_height - height))
        return BoundingBox(x=x, y=y, width=width, height=height)

    def _fit_mobile_aspect(
        self,
        bbox: BoundingBox,
        page: Page,
        *,
        anchor: BoundingBox | None = None,
        min_height: float | None = None,
    ) -> BoundingBox:
        """Frame a vertical reading band at full page width; letterbox to 9:16 in FFmpeg."""
        if not self._settings.screenshot_mobile_crop:
            return bbox

        anchor_bbox = anchor or bbox
        page_width, page_height = self._page_size(page, bbox)
        width = page_width

        floor_height = min_height or 0.0
        content_height = max(bbox.height, anchor_bbox.height * 8.0, floor_height)
        max_height = page_height * 0.92
        height = min(max(content_height, floor_height), max_height)

        if height >= page_height * 0.65:
            y = 0.0
            height = min(page_height * 0.92, page_height)
        else:
            center_y = anchor_bbox.y + anchor_bbox.height / 2
            y = max(0.0, min(center_y - height * 0.45, page_height - height))

        return BoundingBox(x=0.0, y=y, width=width, height=height)

    def _page_size(self, page: Page, bbox: BoundingBox) -> tuple[float, float]:
        page_width = page.width or bbox.x + bbox.width
        page_height = page.height or bbox.y + bbox.height
        return page_width, page_height
