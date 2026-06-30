"""LLM-backed paper brief generation stage."""

from app.config import Settings, get_settings
from app.models.pipeline import ContentPlan
from app.services.paper_brief_generator import PaperBriefGenerator
from app.workflows.stage import Stage


class PaperBriefStage(Stage[ContentPlan, ContentPlan]):
    """Synthesize structured paper understanding before storyboard planning."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        generator: PaperBriefGenerator | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._generator = generator or PaperBriefGenerator(settings=self._settings)

    @property
    def name(self) -> str:
        return "paper_brief"

    def run(self, input_model: ContentPlan) -> ContentPlan:
        brief = self._generator.generate_brief(input_model)
        return input_model.model_copy(update={"paper_brief": brief})
