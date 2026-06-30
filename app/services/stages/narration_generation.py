"""Storyboard-driven narration materialization stage."""

from app.models.narration import Narration
from app.models.pipeline import NarrationPlan, ScreenshotPlan
from app.workflows.stage import Stage


class NarrationGenerationStage(Stage[ScreenshotPlan, NarrationPlan]):
    """Materialize voiceover scripts from the planned storyboard scenes."""

    @property
    def name(self) -> str:
        return "narration_generation"

    def run(self, input_model: ScreenshotPlan) -> NarrationPlan:
        narrations = [
            Narration(
                scene_id=scene.id,
                text=scene.narration,
                estimated_duration_seconds=scene.duration_seconds,
            )
            for scene in input_model.storyboard_result.storyboard.scenes
        ]
        return NarrationPlan(screenshot_plan=input_model, narrations=narrations)
