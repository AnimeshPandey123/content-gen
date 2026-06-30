.PHONY: install lint test test-cov check-gemini run

PYTHON ?= python3
VENV := .venv
BIN := $(VENV)/bin
PDF ?= pdf/paper.pdf
PROJECT_ID ?=

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

check-gemini:
	$(BIN)/python scripts/check_gemini.py

# Examples:
#   make run
#   make run PDF=pdf/attention.pdf
#   make run PDF=pdf/attention.pdf PROJECT_ID=88adcb5b-536e-4c52-b52b-04d353bce1fe
run:
	$(BIN)/python -m app.main $(PDF) $(if $(PROJECT_ID),--project-id $(PROJECT_ID),)
