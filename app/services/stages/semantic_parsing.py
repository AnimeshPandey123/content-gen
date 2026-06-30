"""Semantic document parsing stage."""

from app.config import Settings, get_settings
from app.models.document import Document
from app.services.semantic_parser import SemanticParser
from app.workflows.stage import Stage


class SemanticParsingStage(Stage[Document, Document]):
    """Transform raw extracted pages into a semantic document model."""

    def __init__(self, *, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def name(self) -> str:
        return "semantic_parsing"

    def run(self, input_model: Document) -> Document:
        parser = SemanticParser(output_dir=self._settings.output_dir)
        return parser.enrich(input_model)
