.PHONY: install lint test

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
