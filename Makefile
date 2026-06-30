.PHONY: install lint test test-cov

PYTHON ?= python3
VENV := .venv
BIN := $(VENV)/bin

install:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install -e ".[dev]"

lint:
	$(BIN)/ruff check app tests
	$(BIN)/ruff format --check app tests

test:
	$(BIN)/pytest

test-cov:
	$(BIN)/pytest --cov=app --cov-report=term-missing --cov-fail-under=100 tests
