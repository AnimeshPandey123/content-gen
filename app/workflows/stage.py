"""Workflow stage interface definitions."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class Stage(ABC, Generic[InputT, OutputT]):
    """Base interface for a deterministic or agent-backed pipeline stage.

    Stages are loosely coupled: they never call other stages directly.
    The workflow coordinator is responsible for orchestration.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable stage identifier used in logs."""

    @abstractmethod
    def run(self, input_model: InputT) -> OutputT:
        """Execute the stage and return a validated output model."""
