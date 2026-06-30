"""Storyboard-driven caption materialization stage."""

from app.models.caption import Caption
from app.models.pipeline import CaptionPlan, NarrationPlan
from app.workflows.stage import Stage


class CaptionGenerationStage(Stage[NarrationPlan, CaptionPlan]):
    """Materialize timed captions from the planned storyboard scenes."""

    @property
    def name(self) -> str:
        return "caption_generation"

    def run(self, input_model: NarrationPlan) -> CaptionPlan:
        captions: list[Caption] = []
        start_time = 0.0

        for scene in input_model.screenshot_plan.storyboard_result.storyboard.scenes:
            end_time = start_time + scene.duration_seconds
            captions.append(
                Caption(
                    scene_id=scene.id,
                    text=scene.caption,
                    start_time=start_time,
                    end_time=end_time,
                ),
            )
            start_time = end_time

        return CaptionPlan(narration_plan=input_model, captions=captions)
