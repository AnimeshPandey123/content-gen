"""Tests for environment-driven configuration."""

from pathlib import Path

import pytest
from app.config import Settings, reset_settings


def test_settings_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.gemini_model == "gemini-2.0-flash"
    assert settings.section_selection_limit == 5
    assert settings.storyboard_max_scenes == 8
    assert settings.screenshot_dpi == 300
    assert settings.camera_motion == "ken_burns"
    assert settings.video_width == 1080
    assert settings.video_height == 1920
    assert settings.narration_speed == 1.0
    assert settings.max_retries == 3
    assert settings.screenshot_padding == 4.0


def test_settings_from_environment(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-pro")
    monkeypatch.setenv("SECTION_SELECTION_LIMIT", "3")
    monkeypatch.setenv("STORYBOARD_MAX_SCENES", "4")
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("VIDEO_WIDTH", "720")
    monkeypatch.setenv("VIDEO_HEIGHT", "1280")
    monkeypatch.setenv("NARRATION_SPEED", "1.25")
    monkeypatch.setenv("MAX_RETRIES", "5")
    monkeypatch.setenv("SCREENSHOT_PADDING", "0")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_JSON", "true")

    reset_settings()
    settings = Settings()
    assert settings.gemini_api_key == "test-key"
    assert settings.gemini_model == "gemini-2.5-pro"
    assert settings.section_selection_limit == 3
    assert settings.storyboard_max_scenes == 4
    assert settings.output_dir == Path(tmp_path)
    assert settings.video_width == 720
    assert settings.video_height == 1280
    assert settings.narration_speed == 1.25
    assert settings.max_retries == 5
    assert settings.screenshot_padding == 0.0
    assert settings.log_level == "DEBUG"
    assert settings.log_json is True


def test_section_selection_limit_cannot_exceed_five() -> None:
    with pytest.raises(ValueError):
        Settings(section_selection_limit=6)
