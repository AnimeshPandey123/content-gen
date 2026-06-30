"""Screenshot planning stage."""

from app.config import Settings, get_settings
from app.models.pipeline import ScreenshotPlan, StoryboardResult
from app.services.screenshot_region_planner import ScreenshotRegionPlanner
from app.workflows.stage import Stage


class ScreenshotPlanningStage(Stage[StoryboardResult, ScreenshotPlan]):
    """Plan PDF screenshot regions from semantic paragraph layout."""

    def __init__(self, *, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def name(self) -> str:
        return "screenshot_planning"

    def run(self, input_model: StoryboardResult) -> ScreenshotPlan:
        planner = ScreenshotRegionPlanner(settings=self._settings)
        regions = planner.plan_for_storyboard(input_model)
        return ScreenshotPlan(storyboard_result=input_model, regions=regions)
