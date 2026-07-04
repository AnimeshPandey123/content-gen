"""Resolve marker highlight regions from storyboard shot metadata."""

from app.config import Settings, get_settings
from app.models.bounding_box import BoundingBox, intersect_bbox
from app.models.document import Document
from app.models.scene import SceneShot
from app.services.figure_detector import FigureDetector
from app.services.screenshot_region_planner import ScreenshotRegionPlanner


class HighlightResolver:
    """Map storyboard marker_highlight flags to PDF bounding boxes."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        region_planner: ScreenshotRegionPlanner | None = None,
        figure_detector: FigureDetector | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._region_planner = region_planner or ScreenshotRegionPlanner(settings=self._settings)
        self._figure_detector = figure_detector or FigureDetector()

    def resolve(self, document: Document, shot: SceneShot) -> list[BoundingBox]:
        """Return highlight boxes in page coordinates for a storyboard shot."""
        if not self._settings.highlight_enabled or not shot.marker_highlight:
            return []

        source_bbox = self._source_bbox(document, shot)
        if source_bbox is None:
            return []

        intersection = intersect_bbox(source_bbox, shot.crop)
        if intersection is None:
            return []
        return [intersection]

    def _source_bbox(self, document: Document, shot: SceneShot) -> BoundingBox | None:
        if shot.visual:
            visual = self._figure_detector.find_visual(document, shot.visual)
            if visual is None:
                return None
            return visual.bbox

        try:
            paragraph_ref = self._region_planner.get_paragraph(document, shot.paragraph)
        except Exception:
            return None

        return paragraph_ref.block.bbox
