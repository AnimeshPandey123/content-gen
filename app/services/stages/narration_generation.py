"""Placeholder narration generation stage."""

from app.models.narration import Narration
from app.models.pipeline import NarrationPlan, ScreenshotPlan
from app.workflows.stage import Stage


class NarrationGenerationStage(Stage[ScreenshotPlan, NarrationPlan]):
    """Generate voiceover scripts per scene (placeholder)."""

    @property
    def name(self) -> str:
        return "narration_generation"

    def run(self, input_model: ScreenshotPlan) -> NarrationPlan:
        scene = input_model.storyboard_result.storyboard.scenes[0]
        section = input_model.storyboard_result.content_plan.selected_sections[0]
        narration = Narration(
            scene_id=scene.id,
            text=f"Here is a quick look at {section.title}.",
            estimated_duration_seconds=scene.duration_seconds,
        )
        return NarrationPlan(screenshot_plan=input_model, narrations=[narration])
