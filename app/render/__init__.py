"""Video rendering utilities."""

from app.render.assembler import VideoAssembler
from app.render.camera import CameraMotion, build_video_filter
from app.render.ffmpeg import FFmpegError, FFmpegRenderer
from app.render.project import (
    audio_path,
    bootstrap_render_project,
    clip_path,
    final_video_path,
    scene_basename,
    screenshot_path,
    subtitle_path,
)
from app.render.screenshot import ScreenshotGenerator, ScreenshotGeneratorError
from app.render.subtitles import SubtitleGenerator
from app.render.voice import (
    GeminiVoiceSynthesizer,
    VoiceGenerator,
    VoiceGeneratorError,
    VoiceSynthesizer,
    WaveVoiceSynthesizer,
    build_voice_synthesizer,
)

__all__ = [
    "CameraMotion",
    "FFmpegError",
    "FFmpegRenderer",
    "ScreenshotGenerator",
    "ScreenshotGeneratorError",
    "SubtitleGenerator",
    "VideoAssembler",
    "GeminiVoiceSynthesizer",
    "VoiceGenerator",
    "VoiceGeneratorError",
    "VoiceSynthesizer",
    "WaveVoiceSynthesizer",
    "build_voice_synthesizer",
    "audio_path",
    "bootstrap_render_project",
    "build_video_filter",
    "clip_path",
    "final_video_path",
    "scene_basename",
    "screenshot_path",
    "subtitle_path",
]
