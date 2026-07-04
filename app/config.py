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
    max_sections: int = Field(
        default=15,
        ge=1,
        le=20,
        description="Safety ceiling on sections returned by the LLM",
    )
    max_storyboard_scenes: int = Field(
        default=20,
        ge=1,
        le=20,
        description="Safety ceiling on content scenes returned by the LLM",
    )
    max_shots_per_scene: int = Field(
        default=8,
        ge=1,
        le=8,
        description="Safety ceiling on camera shots per scene in the LLM response",
    )
    max_video_duration_seconds: float = Field(
        default=120.0,
        ge=5.0,
        le=120.0,
        description="Hard safety ceiling when fitting final video duration",
    )

    # Paths
    output_dir: Path = Field(default=Path("output"), description="Directory for generated assets")
    page_image_dpi: int = Field(default=150, ge=72, description="DPI for rendered page images")
    screenshot_padding: float = Field(
        default=24.0,
        ge=0,
        description="Padding in PDF points added around screenshot regions",
    )
    screenshot_expand_factor: float = Field(
        default=3.0,
        ge=1.0,
        description="Multiplier applied to focus-shot screenshot width/height for more context",
    )
    screenshot_highlight_expand_factor: float = Field(
        default=2.5,
        ge=1.0,
        description="Multiplier applied to highlight-shot crops (wider than a tight detail)",
    )
    screenshot_focus_min_height: float = Field(
        default=280.0,
        ge=48.0,
        description="Minimum PDF crop height for focus shots (points)",
    )
    screenshot_highlight_min_height: float = Field(
        default=200.0,
        ge=48.0,
        description="Minimum PDF crop height for highlight shots (points)",
    )
    screenshot_mobile_crop: bool = Field(
        default=True,
        description="Use full page width and frame a vertical reading band (9:16 fit happens in FFmpeg)",
    )
    highlight_enabled: bool = Field(
        default=True,
        description="Draw marker highlights on shots flagged by the storyboard",
    )
    highlight_opacity: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Opacity of marker highlight fills baked into screenshots",
    )
    highlight_color_r: float = Field(default=1.0, ge=0.0, le=1.0)
    highlight_color_g: float = Field(default=0.92, ge=0.0, le=1.0)
    highlight_color_b: float = Field(default=0.23, ge=0.0, le=1.0)

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
        default="static",
        description="Camera motion style: static, zoom, pan, ken_burns, highlight",
    )
    scene_transition: str = Field(
        default="cut",
        description="Transition between scene clips: cut (synced) or crossfade",
    )
    scene_transition_duration: float = Field(
        default=0.5,
        ge=0.1,
        le=2.0,
        description="Crossfade duration in seconds between scene clips",
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
        description="Voice backend: gemini, chatterbox (local API), or silent (placeholder WAV)",
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
    tts_fit_scene_duration: bool = Field(
        default=True,
        description="Speed up TTS audio slightly when it exceeds the scene duration budget",
    )
    tts_max_tempo: float = Field(
        default=1.35,
        ge=1.0,
        le=2.0,
        description="Maximum narration speed-up applied when fitting scene duration",
    )
    chatterbox_api_url: str = Field(
        default="http://192.168.0.158:8000",
        description="Base URL for a locally hosted Chatterbox TTS API (OpenAI-compatible)",
    )
    chatterbox_voice: str | None = Field(
        default=None,
        description="Voice name in the Chatterbox voice library (server default when unset)",
    )
    chatterbox_exaggeration: float = Field(
        default=0.5,
        ge=0.25,
        le=2.0,
        description="Chatterbox emotion intensity (exaggeration parameter)",
    )
    chatterbox_cfg_weight: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Chatterbox pace control (cfg_weight parameter)",
    )
    chatterbox_temperature: float = Field(
        default=0.8,
        ge=0.05,
        le=5.0,
        description="Chatterbox sampling randomness (temperature parameter)",
    )
    chatterbox_request_timeout_seconds: float = Field(
        default=120.0,
        ge=1.0,
        description="HTTP timeout for Chatterbox TTS requests",
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
