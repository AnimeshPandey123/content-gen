"""Tests for environment-driven configuration."""

from pathlib import Path

from app.config import Settings, get_settings, reset_settings


def test_settings_defaults() -> None:
    reset_settings()
    settings = get_settings()
    assert settings.model_name == "gpt-4o"
    assert settings.video_width == 1080
    assert settings.video_height == 1920
    assert settings.narration_speed == 1.0
    assert settings.max_retries == 3


def test_settings_from_environment(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("MODEL_NAME", "gpt-4o-mini")
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("VIDEO_WIDTH", "720")
    monkeypatch.setenv("VIDEO_HEIGHT", "1280")
    monkeypatch.setenv("NARRATION_SPEED", "1.25")
    monkeypatch.setenv("MAX_RETRIES", "5")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_JSON", "true")

    reset_settings()
    settings = Settings()
    assert settings.model_name == "gpt-4o-mini"
    assert settings.output_dir == Path(tmp_path)
    assert settings.video_width == 720
    assert settings.video_height == 1280
    assert settings.narration_speed == 1.25
    assert settings.max_retries == 5
    assert settings.log_level == "DEBUG"
    assert settings.log_json is True
