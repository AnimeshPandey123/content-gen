"""Prompt templates for script generation."""

from app.config import Settings, get_settings
from app.models.pipeline import StoryboardResult
from app.services.duration_budget import playback_duration


def build_script_prompt(
    storyboard_result: StoryboardResult,
    *,
    settings: Settings | None = None,
) -> str:
    """Build the Gemini prompt for generating the video script."""
    settings = settings or get_settings()
    scenes = "\n".join(
        _format_scene(scene, words_per_minute=settings.words_per_minute)
        for scene in storyboard_result.storyboard.scenes
    )
    document_title = storyboard_result.content_plan.document.title or "Untitled"
    durations = [scene.duration_seconds for scene in storyboard_result.storyboard.scenes]
    total_duration = playback_duration(
        durations,
        transition_duration_seconds=settings.scene_transition_duration,
    )

    return f"""You are writing a short-form vertical video script from a storyboard.

Document title: {document_title}

The finished video must be at most {settings.max_video_duration_seconds:.0f} seconds.
Current storyboard playback budget: {total_duration:.1f} seconds.

Storyboard:
{scenes}

Write one script entry per storyboard scene.
Return JSON with this exact shape:
{{
  "scenes": [
    {{
      "scene": 1,
      "voice": "This paper proposes a new way to train language models using less data.",
      "overlay": "Train AI with Less Data",
      "duration": 6.0
    }}
  ]
}}

Rules:
- scene numbers must match the storyboard scene numbers exactly.
- voice must be brief enough to speak naturally within each scene duration.
- use the max word count shown for each scene as a hard ceiling.
- overlay should be short, punchy, and readable on a phone screen.
- duration should match the storyboard target duration for each scene.
- Do not add extra scenes.
"""


def _format_scene(scene, *, words_per_minute: int) -> str:
    max_words = max(int(scene.duration_seconds * words_per_minute / 60), 1)
    return (
        f"- Scene {scene.order + 1}: {scene.goal}\n"
        f"  Duration: {scene.duration_seconds}s\n"
        f"  Max voice words: {max_words}\n"
        f"  Source: {scene.source.section}, page {scene.source.page}, "
        f"paragraph {scene.source.paragraph}"
    )
