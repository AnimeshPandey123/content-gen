"""CLI entry point for the PDF-to-video pipeline."""

import argparse
import json
import sys

from app.config import get_settings
from app.models.pipeline import PipelineInput
from app.services import build_default_stages
from app.utils.logging import configure_logging, get_logger
from app.workflows import PipelineCoordinator

logger = get_logger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the PDF-to-short-video pipeline")
    parser.add_argument("pdf_path", help="Path to the source PDF")
    parser.add_argument("--project-id", default=None, help="Optional project identifier")
    args = parser.parse_args(argv)

    settings = get_settings()
    configure_logging(log_level=settings.log_level, json_output=settings.log_json)

    pipeline_input = PipelineInput(pdf_path=args.pdf_path, project_id=args.project_id)
    coordinator = PipelineCoordinator(build_default_stages(), settings=settings)

    logger.info("pipeline_start", pdf_path=pipeline_input.pdf_path)
    result = coordinator.execute(pipeline_input)
    logger.info("pipeline_finish", result_type=type(result).__name__)

    print(json.dumps(result.model_dump(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
