"""Unit tests for structured logging utilities."""

import logging

import structlog
from app.utils.logging import configure_logging, get_logger


def test_configure_logging_console_mode() -> None:
    configure_logging(log_level="DEBUG", json_output=False)
    logger = get_logger("test.console")
    logger.info("console log", key="value")


def test_configure_logging_json_mode() -> None:
    configure_logging(log_level="WARNING", json_output=True)
    logger = get_logger("test.json")
    logger.warning("json log", key="value")


def test_configure_logging_unknown_level_defaults_to_info() -> None:
    configure_logging(log_level="NOT_A_LEVEL", json_output=False)
    assert logging.getLogger().level == logging.INFO


def test_get_logger_with_initial_context() -> None:
    configure_logging()
    logger = get_logger("test.context", request_id="abc")
    assert isinstance(logger, structlog.stdlib.BoundLogger)
