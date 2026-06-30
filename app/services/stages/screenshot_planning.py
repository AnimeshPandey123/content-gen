"""Placeholder screenshot planning stage."""

from app.models.pipeline import ScreenshotPlan, StoryboardResult
from app.models.screenshot import ScreenshotRegion
from app.workflows.stage import Stage


class ScreenshotPlanningStage(Stage[StoryboardResult, ScreenshotPlan]):
    """Plan PDF screenshot regions for each scene (placeholder)."""

    @property
    def name(self) -> str:
        return "screenshot_planning"

    def run(self, input_model: StoryboardResult) -> ScreenshotPlan:
        scene = input_model.storyboard.scenes[0]
        page = input_model.content_plan.document.pages[0]
        region = ScreenshotRegion(
            scene_id=scene.id,
            page_number=page.page_number,
            x=0.0,
            y=0.0,
            width=page.width or 612.0,
            height=page.height or 792.0,
        )
        return ScreenshotPlan(storyboard_result=input_model, regions=[region])
