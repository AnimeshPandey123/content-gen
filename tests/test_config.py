"""Tests for environment-driven configuration."""

from pathlib import Path

import pytest
from app.config import Settings, reset_settings


def test_settings_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.gemini_model == "gemini-2.0-flash"
    assert settings.max_sections == 15
    assert settings.max_storyboard_scenes == 20
    assert settings.max_video_duration_seconds == 120.0
    assert settings.max_shots_per_scene == 8
    assert settings.screenshot_dpi == 300
    assert settings.camera_motion == "static"
    assert settings.scene_transition == "cut"
    assert settings.scene_transition_duration == 0.5
    assert settings.video_width == 1080
    assert settings.video_height == 1920
    assert settings.narration_speed == 1.0
    assert settings.voice_synthesizer == "gemini"
    assert settings.tts_model == "gemini-2.5-flash-preview-tts"
    assert settings.tts_voice == "Kore"
    assert settings.tts_sample_rate == 24000
    assert settings.max_retries == 3
    assert settings.screenshot_padding == 24.0
    assert settings.screenshot_expand_factor == 3.0
    assert settings.screenshot_highlight_expand_factor == 2.5
    assert settings.screenshot_focus_min_height == 280.0
    assert settings.screenshot_highlight_min_height == 200.0
    assert settings.screenshot_mobile_crop is True


def test_settings_from_environment(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-pro")
    monkeypatch.setenv("MAX_SECTIONS", "3")
    monkeypatch.setenv("MAX_STORYBOARD_SCENES", "6")
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("VIDEO_WIDTH", "720")
    monkeypatch.setenv("VIDEO_HEIGHT", "1280")
    monkeypatch.setenv("NARRATION_SPEED", "1.25")
    monkeypatch.setenv("VOICE_SYNTHESIZER", "silent")
    monkeypatch.setenv("TTS_MODEL", "gemini-2.5-flash-preview-tts")
    monkeypatch.setenv("TTS_VOICE", "Puck")
    monkeypatch.setenv("TTS_SAMPLE_RATE", "22050")
    monkeypatch.setenv("MAX_RETRIES", "5")
    monkeypatch.setenv("SCREENSHOT_PADDING", "0")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_JSON", "true")

    reset_settings()
    settings = Settings()
    assert settings.gemini_api_key == "test-key"
    assert settings.gemini_model == "gemini-2.5-pro"
    assert settings.max_sections == 3
    assert settings.max_storyboard_scenes == 6
    assert settings.output_dir == Path(tmp_path)
    assert settings.video_width == 720
    assert settings.video_height == 1280
    assert settings.narration_speed == 1.25
    assert settings.voice_synthesizer == "silent"
    assert settings.tts_voice == "Puck"
    assert settings.tts_sample_rate == 22050
    assert settings.max_retries == 5
    assert settings.screenshot_padding == 0.0
    assert settings.log_level == "DEBUG"
    assert settings.log_json is True


def test_max_sections_cannot_exceed_twenty() -> None:
    with pytest.raises(ValueError):
        Settings(max_sections=21)
