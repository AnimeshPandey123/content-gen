"""Unit tests for workflow coordinator execution."""

import time

import pytest
from app.config import Settings
from app.models.pipeline import PipelineInput, RenderResult
from app.services import build_default_stages
from app.workflows import PipelineCoordinator, StageExecutionError
from app.workflows.stage import Stage


class _FlakyStage(Stage[PipelineInput, PipelineInput]):
    """Fails a configurable number of times before succeeding."""

    def __init__(self, failures_before_success: int) -> None:
        self._failures_before_success = failures_before_success
        self._attempts = 0

    @property
    def name(self) -> str:
        return "flaky_stage"

    def run(self, input_model: PipelineInput) -> PipelineInput:
        self._attempts += 1
        if self._attempts <= self._failures_before_success:
            raise RuntimeError("transient failure")
        return input_model


class _AlwaysFailStage(Stage[PipelineInput, PipelineInput]):
    @property
    def name(self) -> str:
        return "always_fail"

    def run(self, input_model: PipelineInput) -> PipelineInput:
        raise ValueError("permanent failure")


def test_full_pipeline_execution(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))

    coordinator = PipelineCoordinator(build_default_stages())
    result = coordinator.execute(PipelineInput(pdf_path="/tmp/sample.pdf", project_id="proj-1"))

    assert isinstance(result, RenderResult)
    assert result.success is True
    assert result.project.document.id == "proj-1"
    assert result.project.storyboard.document_id == "proj-1"
    assert len(result.project.captions) >= 1


def test_coordinator_retries_transient_failures() -> None:
    settings = Settings(max_retries=2, retry_delay_seconds=0)
    stage = _FlakyStage(failures_before_success=2)
    coordinator = PipelineCoordinator([stage], settings=settings)

    result = coordinator.execute(PipelineInput(pdf_path="/tmp/x.pdf"))
    assert isinstance(result, PipelineInput)
    assert stage._attempts == 3


def test_coordinator_raises_after_exhausted_retries() -> None:
    settings = Settings(max_retries=1, retry_delay_seconds=0)
    coordinator = PipelineCoordinator([_AlwaysFailStage()], settings=settings)

    with pytest.raises(StageExecutionError) as exc_info:
        coordinator.execute(PipelineInput(pdf_path="/tmp/x.pdf"))

    assert exc_info.value.stage_name == "always_fail"
    assert exc_info.value.attempts == 2


def test_coordinator_chains_multiple_stages() -> None:
    from app.models.document import Document
    from app.services.stages.document_extraction import DocumentExtractionStage

    class _PassThroughStage(Stage[PipelineInput, PipelineInput]):
        @property
        def name(self) -> str:
            return "pass_through"

        def run(self, input_model: PipelineInput) -> PipelineInput:
            return input_model

    coordinator = PipelineCoordinator(
        [_PassThroughStage(), DocumentExtractionStage()],
        settings=Settings(max_retries=0),
    )
    result = coordinator.execute(PipelineInput(pdf_path="/tmp/ok.pdf"))
    assert isinstance(result, Document)
    assert result.source_path == "/tmp/ok.pdf"


def test_stage_execution_logs_timing(monkeypatch) -> None:
    monkeypatch.setenv("OUTPUT_DIR", "output")

    class _SlowStage(Stage[PipelineInput, PipelineInput]):
        @property
        def name(self) -> str:
            return "slow_stage"

        def run(self, input_model: PipelineInput) -> PipelineInput:
            time.sleep(0.01)
            return input_model

    coordinator = PipelineCoordinator(
        [_SlowStage()],
        settings=Settings(max_retries=0, retry_delay_seconds=0),
    )
    result = coordinator.execute(PipelineInput(pdf_path="/tmp/x.pdf"))
    assert result.pdf_path == "/tmp/x.pdf"
