"""Placeholder content planning stage."""

from app.models.document import Document
from app.models.pipeline import ContentPlan
from app.models.section import Section
from app.workflows.stage import Stage


class ContentPlanningStage(Stage[Document, ContentPlan]):
    """Select interesting sections from the document (placeholder)."""

    @property
    def name(self) -> str:
        return "content_planning"

    def run(self, input_model: Document) -> ContentPlan:
        section = Section(
            id=f"{input_model.id}-section-1",
            title="Key Highlight",
            content=input_model.pages[0].text,
            page_numbers=[input_model.pages[0].page_number],
            importance_score=0.9,
        )
        return ContentPlan(document=input_model, selected_sections=[section])
