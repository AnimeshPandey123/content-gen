"""Centralized, environment-driven configuration."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    gemini_api_key: str | None = Field(
        default=None,
        description="Google Gemini API key for LLM stages",
    )
    gemini_model: str = Field(
        default="gemini-2.0-flash",
        description="Gemini model used for LLM stages",
    )
    section_selection_limit: int = Field(
        default=5,
        ge=1,
        le=5,
        description="Maximum number of sections to select for the video",
    )
    storyboard_max_scenes: int = Field(
        default=8,
        ge=1,
        le=20,
        description="Maximum number of scenes in the generated storyboard",
    )

    # Paths
    output_dir: Path = Field(default=Path("output"), description="Directory for generated assets")
    page_image_dpi: int = Field(default=150, ge=72, description="DPI for rendered page images")
    screenshot_padding: float = Field(
        default=4.0,
        ge=0,
        description="Padding in PDF points added around paragraph screenshot regions",
    )

    # Video rendering
    video_width: int = Field(default=1080, ge=1)
    video_height: int = Field(default=1920, ge=1)
    video_fps: int = Field(default=30, ge=1)
    screenshot_dpi: int = Field(
        default=300,
        ge=72,
        description="DPI for high-resolution PDF screenshot crops",
    )
    camera_motion: str = Field(
        default="ken_burns",
        description="Camera motion style: static, zoom, pan, ken_burns, highlight",
    )
    ffmpeg_path: str = Field(default="ffmpeg", description="Path to the FFmpeg binary")
    subtitle_font_size: int = Field(default=72, ge=12, description="ASS subtitle font size")
    words_per_minute: int = Field(
        default=150,
        ge=60,
        description="Speaking rate used to estimate narration duration",
    )

    # Narration / TTS
    narration_speed: float = Field(default=1.0, gt=0, description="Playback speed multiplier")
    voice_synthesizer: str = Field(
        default="gemini",
        description="Voice backend: gemini (Gemini TTS) or silent (placeholder WAV)",
    )
    tts_model: str = Field(
        default="gemini-2.5-flash-preview-tts",
        description="Gemini model for text-to-speech generation",
    )
    tts_voice: str = Field(
        default="Kore",
        description="Prebuilt Gemini TTS voice name",
    )
    tts_sample_rate: int = Field(
        default=24000,
        ge=8000,
        description="Sample rate for Gemini TTS WAV output",
    )

    # Workflow
    max_retries: int = Field(default=3, ge=0)
    retry_delay_seconds: float = Field(default=1.0, ge=0)

    # Logging
    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=False, description="Emit logs as JSON when True")


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return cached settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Clear cached settings (useful in tests)."""
    global _settings
    _settings = None
