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
    model_name: str = Field(default="gpt-4o", description="LLM model for planning stages")

    # Paths
    output_dir: Path = Field(default=Path("output"), description="Directory for generated assets")

    # Video rendering
    video_width: int = Field(default=1080, ge=1)
    video_height: int = Field(default=1920, ge=1)
    video_fps: int = Field(default=30, ge=1)

    # Narration
    narration_speed: float = Field(default=1.0, gt=0, description="Playback speed multiplier")

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
