"""Sequential workflow coordinator with validation, logging, and retries."""

import time
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ValidationError

from app.config import Settings, get_settings
from app.utils.logging import get_logger
from app.workflows.stage import Stage

logger = get_logger(__name__)


class StageExecutionError(Exception):
    """Raised when a stage fails after all retry attempts."""

    def __init__(self, stage_name: str, attempts: int, cause: Exception) -> None:
        self.stage_name = stage_name
        self.attempts = attempts
        self.cause = cause
        super().__init__(f"Stage '{stage_name}' failed after {attempts} attempt(s): {cause}")


class PipelineCoordinator:
    """Executes pipeline stages sequentially, passing outputs to the next stage."""

    def __init__(
        self,
        stages: Sequence[Stage[Any, Any]],
        *,
        settings: Settings | None = None,
    ) -> None:
        self._stages = list(stages)
        self._settings = settings or get_settings()

    @property
    def stages(self) -> list[Stage[Any, Any]]:
        return list(self._stages)

    def execute(self, initial_input: BaseModel) -> BaseModel:
        """Run all stages in order, returning the final stage output."""
        current: BaseModel = initial_input

        for stage in self._stages:
            current = self._run_stage_with_retries(stage, current)

        return current

    def _run_stage_with_retries(self, stage: Stage[Any, Any], input_model: BaseModel) -> BaseModel:
        stage_name = stage.name
        max_attempts = self._settings.max_retries + 1
        delay = self._settings.retry_delay_seconds

        self._validate_input(stage_name, input_model)

        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            started = time.perf_counter()
            log = logger.bind(stage=stage_name, attempt=attempt, max_attempts=max_attempts)

            log.info("stage_start")

            try:
                output = stage.run(input_model)
                self._validate_output(stage_name, output)
                elapsed = time.perf_counter() - started
                log.info("stage_finish", duration_seconds=round(elapsed, 4))
                return output
            except Exception as exc:
                elapsed = time.perf_counter() - started
                last_error = exc
                will_retry = attempt < max_attempts

                log.error(
                    "stage_failure",
                    duration_seconds=round(elapsed, 4),
                    error=str(exc),
                    error_type=type(exc).__name__,
                    will_retry=will_retry,
                )

                if will_retry:
                    log.warning("stage_retry", retry_delay_seconds=delay)
                    if delay > 0:
                        time.sleep(delay)
                else:
                    log.error("stage_exhausted_retries", attempts=attempt)

        assert last_error is not None
        raise StageExecutionError(stage_name, max_attempts, last_error) from last_error

    def _validate_input(self, stage_name: str, model: BaseModel) -> None:
        try:
            model.model_validate(model.model_dump())
        except ValidationError as exc:
            logger.error("stage_input_validation_failed", stage=stage_name, errors=exc.errors())
            raise

    def _validate_output(self, stage_name: str, model: BaseModel) -> None:
        try:
            model.model_validate(model.model_dump())
        except ValidationError as exc:
            logger.error("stage_output_validation_failed", stage=stage_name, errors=exc.errors())
            raise
