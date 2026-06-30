"""Shared test fixtures."""

import pytest
from app.config import reset_settings


@pytest.fixture(autouse=True)
def _reset_settings() -> None:
    reset_settings()
    yield
    reset_settings()
