"""Terminal progress display for long-running pipeline steps."""

from __future__ import annotations

import os
import sys

from app.config import get_settings


def progress_enabled() -> bool:
    """Show live progress when stderr is a TTY and logs are not JSON."""
    if "PYTEST_CURRENT_TEST" in os.environ:
        return False
    return sys.stderr.isatty() and not get_settings().log_json


class TaskProgress:
    """Simple stderr progress bar for multi-step tasks."""

    def __init__(
        self,
        label: str,
        total: int,
        *,
        enabled: bool | None = None,
        width: int = 28,
    ) -> None:
        self._label = label
        self._total = max(total, 1)
        self._current = 0
        self._enabled = progress_enabled() if enabled is None else enabled
        self._width = width

    def step(self, *, message: str = "") -> None:
        """Advance one step and refresh the display."""
        self._current = min(self._current + 1, self._total)
        self._render(message)

    def finish(self, *, message: str = "") -> None:
        """Complete the bar and move to the next line."""
        if not self._enabled:
            return
        if self._current < self._total:
            self._current = self._total
            self._render(message)
        sys.stderr.write("\n")
        sys.stderr.flush()

    def _render(self, message: str) -> None:
        if not self._enabled:
            return
        filled = int(self._width * self._current / self._total)
        bar = "█" * filled + "░" * (self._width - filled)
        line = f"\r{self._label} [{bar}] {self._current}/{self._total}"
        if message:
            line += f"  {message}"
        sys.stderr.write(line)
        sys.stderr.flush()
