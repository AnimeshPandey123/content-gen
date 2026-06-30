"""Prompt templates for script generation."""

from app.models.pipeline import StoryboardResult


def build_script_prompt(storyboard_result: StoryboardResult) -> str:
    """Build the Gemini prompt for generating the video script."""
    scenes = "\n".join(_format_scene(scene) for scene in storyboard_result.storyboard.scenes)
    document_title = storyboard_result.content_plan.document.title or "Untitled"

    return f"""You are writing a short-form vertical video script from a storyboard.

Document title: {document_title}

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
      "duration": 8.0
    }}
  ]
}}

Rules:
- scene numbers must match the storyboard scene numbers exactly.
- voice should sound natural when spoken aloud.
- overlay should be short, punchy, and readable on a phone screen.
- duration should stay close to the storyboard target duration.
- Do not add extra scenes.
"""


def _format_scene(scene) -> str:
    return (
        f"- Scene {scene.order + 1}: {scene.goal}\n"
        f"  Duration: {scene.duration_seconds}s\n"
        f"  Source: {scene.source.section}, page {scene.source.page}, "
        f"paragraph {scene.source.paragraph}"
    )
