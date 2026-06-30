"""Placeholder document extraction stage."""

import uuid

from app.models.document import Document
from app.models.page import Page
from app.models.pipeline import PipelineInput
from app.workflows.stage import Stage


class DocumentExtractionStage(Stage[PipelineInput, Document]):
    """Extract structured document data from a PDF (placeholder)."""

    @property
    def name(self) -> str:
        return "document_extraction"

    def run(self, input_model: PipelineInput) -> Document:
        project_id = input_model.project_id or str(uuid.uuid4())
        return Document(
            id=project_id,
            source_path=input_model.pdf_path,
            title="Placeholder Document",
            pages=[
                Page(page_number=1, text="Placeholder page content.", width=612.0, height=792.0),
            ],
        )
