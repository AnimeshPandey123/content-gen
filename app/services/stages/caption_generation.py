"""Placeholder caption generation stage."""

from app.models.caption import Caption
from app.models.pipeline import CaptionPlan, NarrationPlan
from app.workflows.stage import Stage


class CaptionGenerationStage(Stage[NarrationPlan, CaptionPlan]):
    """Generate timed captions from narration (placeholder)."""

    @property
    def name(self) -> str:
        return "caption_generation"

    def run(self, input_model: NarrationPlan) -> CaptionPlan:
        narration = input_model.narrations[0]
        caption = Caption(
            scene_id=narration.scene_id,
            text=narration.text,
            start_time=0.0,
            end_time=narration.estimated_duration_seconds,
        )
        return CaptionPlan(narration_plan=input_model, captions=[caption])
