"""Unit tests for the CLI entry point."""

import json
import runpy
import sys

from app.config import reset_settings
from app.main import main


def test_main_runs_pipeline(sample_pdf, tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
    reset_settings()

    code = main([str(sample_pdf), "--project-id", "cli-test"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out[captured.out.index("{") :])
    assert payload["project"]["document"]["id"] == "cli-test"


def test_main_module_entrypoint(sample_pdf, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
    reset_settings()
    exit_codes: list[int] = []
    monkeypatch.setattr(sys, "argv", ["app.main", str(sample_pdf), "--project-id", "entry"])
    monkeypatch.setattr(sys, "exit", lambda code: exit_codes.append(code))

    runpy.run_module("app.main", run_name="__main__")

    assert exit_codes == [0]
