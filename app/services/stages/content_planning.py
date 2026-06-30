"""LLM-backed content planning stage."""

from app.config import Settings, get_settings
from app.models.document import Document
from app.models.pipeline import ContentPlan
from app.services.section_selector import SectionSelector
from app.workflows.stage import Stage


class ContentPlanningStage(Stage[Document, ContentPlan]):
    """Select the top interesting sections from the document using Gemini."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        selector: SectionSelector | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._selector = selector or SectionSelector(settings=self._settings)

    @property
    def name(self) -> str:
        return "content_planning"

    def run(self, input_model: Document) -> ContentPlan:
        sections = self._selector.select_sections(input_model)
        return ContentPlan(document=input_model, selected_sections=sections)
