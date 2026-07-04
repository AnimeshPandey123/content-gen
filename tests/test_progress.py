"""Unit tests for terminal progress display."""

import io

from app.utils.progress import TaskProgress, progress_enabled


def test_task_progress_writes_bar_when_enabled(monkeypatch) -> None:
    stderr = io.StringIO()
    monkeypatch.setattr("app.utils.progress.sys.stderr", stderr)

    progress = TaskProgress("video_rendering", 4, enabled=True)
    progress.step(message="scene 01")
    progress.step(message="scene 02")
    progress.finish()

    output = stderr.getvalue()
    assert "video_rendering [" in output
    assert "1/4" in output
    assert "scene 01" in output
    assert "4/4" in output
    assert output.endswith("\n")


def test_task_progress_silent_when_disabled(monkeypatch) -> None:
    stderr = io.StringIO()
    monkeypatch.setattr("app.utils.progress.sys.stderr", stderr)

    progress = TaskProgress("voice_generation", 3, enabled=False)
    progress.step(message="scene 01")
    progress.finish()

    assert stderr.getvalue() == ""


def test_progress_enabled_respects_tty_and_json_logs(monkeypatch) -> None:
    from app.config import reset_settings

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr("app.utils.progress.sys.stderr.isatty", lambda: True)
    monkeypatch.setenv("LOG_JSON", "false")
    reset_settings()
    assert progress_enabled() is True

    monkeypatch.setenv("LOG_JSON", "true")
    reset_settings()
    assert progress_enabled() is False

    reset_settings()
