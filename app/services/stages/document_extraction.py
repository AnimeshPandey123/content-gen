"""Document extraction stage."""

import uuid

from app.config import Settings, get_settings
from app.models.document import Document
from app.models.pipeline import PipelineInput
from app.services.pdf_extractor import PDFExtractor
from app.workflows.stage import Stage


class DocumentExtractionStage(Stage[PipelineInput, Document]):
    """Extract structured document data from a PDF."""

    def __init__(self, *, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def name(self) -> str:
        return "document_extraction"

    def run(self, input_model: PipelineInput) -> Document:
        document_id = input_model.project_id or str(uuid.uuid4())
        extractor = PDFExtractor(
            output_dir=self._settings.output_dir,
            image_dpi=self._settings.page_image_dpi,
        )
        return extractor.extract(input_model.pdf_path, document_id=document_id)
