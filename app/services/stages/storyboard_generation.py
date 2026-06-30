"""Placeholder storyboard generation stage."""

from app.models.pipeline import ContentPlan, StoryboardResult
from app.models.scene import Scene
from app.models.storyboard import Storyboard
from app.workflows.stage import Stage


class StoryboardGenerationStage(Stage[ContentPlan, StoryboardResult]):
    """Create a storyboard from selected content (placeholder)."""

    @property
    def name(self) -> str:
        return "storyboard_generation"

    def run(self, input_model: ContentPlan) -> StoryboardResult:
        section = input_model.selected_sections[0]
        paragraph_index = section.paragraph_indices[0] if section.paragraph_indices else None
        scene = Scene(
            id=f"{input_model.document.id}-scene-1",
            section_id=section.id,
            order=0,
            description=f"Visual summary of: {section.title}",
            duration_seconds=5.0,
            paragraph_index=paragraph_index,
        )
        storyboard = Storyboard(document_id=input_model.document.id, scenes=[scene])
        return StoryboardResult(content_plan=input_model, storyboard=storyboard)
