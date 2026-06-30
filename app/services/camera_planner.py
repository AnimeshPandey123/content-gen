"""Plan and resolve multi-shot camera sequences for storyboard scenes."""

from app.config import Settings, get_settings
from app.models.bounding_box import merge_crop_for_continuity
from app.models.document import Document
from app.models.scene import SceneShot
from app.models.storyboard_generation import PlannedScene, PlannedShot
from app.services.screenshot_region_planner import ScreenshotRegionError, ScreenshotRegionPlanner


def normalize_shot_durations(
    shots: list[PlannedShot],
    scene_duration_seconds: float,
) -> list[PlannedShot]:
    """Scale shot durations so they sum to the scene duration."""
    if not shots:
        return shots

    total = sum(shot.duration_seconds for shot in shots)
    scale = scene_duration_seconds / total
    return [
        shot.model_copy(update={"duration_seconds": round(shot.duration_seconds * scale, 3)})
        for shot in shots
    ]


class CameraPlanner:
    """Resolve LLM-planned shots into concrete PDF crop regions."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        region_planner: ScreenshotRegionPlanner | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._region_planner = region_planner or ScreenshotRegionPlanner(settings=self._settings)

    def resolve_shots(self, planned: PlannedScene, document: Document) -> list[SceneShot]:
        """Return ordered scene shots with resolved crops for a planned scene."""
        if not planned.shots:
            raise ScreenshotRegionError(
                "Storyboard scene has no camera shots; the LLM must plan each frame",
            )

        normalized = normalize_shot_durations(planned.shots, planned.duration_seconds)
        shots: list[SceneShot] = []

        for order, planned_shot in enumerate(normalized):
            try:
                if planned_shot.visual:
                    page_number, crop = self._region_planner.crop_for_visual(
                        document,
                        planned_shot.visual,
                    )
                    paragraph = planned.source.paragraph
                    framing = planned_shot.framing or "focus"
                    visual = planned_shot.visual
                else:
                    page_number, crop = self._region_planner.crop_for_framing(
                        document,
                        page=planned_shot.page,
                        paragraph=planned_shot.paragraph,
                        framing=planned_shot.framing,
                    )
                    paragraph = planned_shot.paragraph
                    framing = planned_shot.framing
                    visual = None
            except ScreenshotRegionError:
                continue

            shots.append(
                SceneShot(
                    order=order,
                    goal=planned_shot.goal,
                    duration_seconds=planned_shot.duration_seconds,
                    page=page_number,
                    paragraph=paragraph,
                    visual=visual,
                    framing=framing,
                    crop=crop,
                ),
            )

        if not shots:
            raise ScreenshotRegionError("No camera shots could be resolved for the planned scene")

        shots = self._align_same_page_crops(document, shots)
        return self._rebalance_shot_durations(shots, planned.duration_seconds)

    def shot_for_page(
        self,
        *,
        document: Document,
        page_number: int,
        paragraph: int,
        goal: str,
        duration_seconds: float,
        framing: str = "wide",
    ) -> SceneShot:
        """Build a single wide shot for title-page style scenes."""
        page_number, crop = self._region_planner.crop_for_framing(
            document,
            page=page_number,
            paragraph=paragraph,
            framing=framing,
        )
        return SceneShot(
            order=0,
            goal=goal,
            duration_seconds=duration_seconds,
            page=page_number,
            paragraph=paragraph,
            framing=framing,
            crop=crop,
        )

    def rebalance_shot_durations(
        self,
        shots: list[SceneShot],
        scene_duration_seconds: float,
    ) -> list[SceneShot]:
        """Scale shot durations so they sum to the scene duration."""
        return self._rebalance_shot_durations(shots, scene_duration_seconds)

    def _align_same_page_crops(
        self,
        document: Document,
        shots: list[SceneShot],
    ) -> list[SceneShot]:
        """Keep text visible when moving from wide to tighter shots on one page."""
        if len(shots) < 2:
            return shots

        aligned: list[SceneShot] = [shots[0]]
        for shot in shots[1:]:
            previous = aligned[-1]
            if shot.page != previous.page:
                aligned.append(shot)
                continue

            page = self._region_planner._get_page(document, shot.page)
            _, page_height = self._region_planner._page_size(page, shot.crop)
            merged = merge_crop_for_continuity(previous.crop, shot.crop, page_height=page_height)
            aligned.append(shot.model_copy(update={"crop": merged}))

        return aligned

    def _rebalance_shot_durations(
        self,
        shots: list[SceneShot],
        scene_duration_seconds: float,
    ) -> list[SceneShot]:
        total = sum(shot.duration_seconds for shot in shots)
        if total <= 0:
            return shots

        scale = scene_duration_seconds / total
        return [
            shot.model_copy(
                update={"duration_seconds": round(shot.duration_seconds * scale, 3)},
            )
            for shot in shots
        ]
