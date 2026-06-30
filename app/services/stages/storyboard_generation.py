"""LLM-backed storyboard generation stage."""

from app.config import Settings, get_settings
from app.models.pipeline import ContentPlan, StoryboardResult
from app.services.storyboard_generator import StoryboardGenerator
from app.workflows.stage import Stage


class StoryboardGenerationStage(Stage[ContentPlan, StoryboardResult]):
    """Plan scenes with goal, duration, source, screenshot, narration, and caption."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        generator: StoryboardGenerator | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._generator = generator or StoryboardGenerator(settings=self._settings)

    @property
    def name(self) -> str:
        return "storyboard_generation"

    def run(self, input_model: ContentPlan) -> StoryboardResult:
        storyboard = self._generator.generate_storyboard(input_model)
        return StoryboardResult(content_plan=input_model, storyboard=storyboard)
