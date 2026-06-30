"""Prompt templates for script generation."""

from app.config import Settings, get_settings
from app.models.pipeline import StoryboardResult
from app.services.duration_budget import playback_duration
from app.services.source_context import format_paper_brief, format_scene_source_context


def build_script_prompt(
    storyboard_result: StoryboardResult,
    *,
    settings: Settings | None = None,
) -> str:
    """Build the Gemini prompt for generating the video script."""
    settings = settings or get_settings()
    document = storyboard_result.content_plan.document
    sections = storyboard_result.content_plan.selected_sections
    scenes = "\n".join(
        _format_scene(
            scene,
            words_per_minute=settings.words_per_minute,
            source_context=format_scene_source_context(document, sections, scene),
        )
        for scene in storyboard_result.storyboard.scenes
    )
    document_title = storyboard_result.content_plan.document.title or "Untitled"
    durations = [scene.duration_seconds for scene in storyboard_result.storyboard.scenes]
    total_duration = playback_duration(
        durations,
        transition_duration_seconds=settings.scene_transition_duration,
    )
    plan = storyboard_result.storyboard.plan
    target_duration = plan.target_video_duration_seconds if plan else total_duration
    brief_block = ""
    if storyboard_result.content_plan.paper_brief is not None:
        brief_block = f"""
Paper brief (ground voiceover in these insights and facts):
{format_paper_brief(storyboard_result.content_plan.paper_brief)}

"""

    return f"""You are writing a short-form vertical video script from a storyboard.
The script should sound informative, energetic, and shareable—like a top science communicator
on TikTok, Reels, or Shorts. Be accurate to the paper; never invent facts or exaggerate results.

Document title: {document_title}
{brief_block}
Target video duration: {target_duration:.1f} seconds.
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
- The opening scene is the automatic title-page intro: write a hook or teaser, not a dry title readout.
- The final scene is the automatic closing scene: voice MUST conclude the video with a clear
  takeaway, significance, or "so what"—do not end on raw results or unfinished technical detail.
- The closing scene must use nearly the full max word count for its duration and match the same
  energy, pace, and sentence style as the middle scenes—never a slow epilogue or one-liner.
- Middle scenes carry the argument; only the final scene should wrap up.
- Each scene includes Source excerpts below—voice MUST use concrete facts from those excerpts.
- Prefer mechanism, numbers, and comparisons over vague praise (avoid "novel approach" without specifics).
- Every middle-scene voice line should teach something non-obvious from the source text.

Tone and style:
- Open with a hook: a question, bold claim, or surprising fact—never "In this paper" or "The authors".
- Use active voice and short sentences; one clear idea per scene; must sound natural read aloud.
- Explain jargon in plain language; prefer specific numbers and comparisons over vague praise.
- overlay: 2-5 words, punchy and readable on a phone; tease the insight (e.g. "2x Faster Training")
  not a dry label (e.g. "Model Architecture Section").
- Avoid academic filler: "we propose", "it is shown that", "in this work", "the following".
- Virality comes from a genuinely interesting insight told clearly—not hype, caps lock, or empty superlatives.
"""


def _format_scene(scene, *, words_per_minute: int, source_context: str) -> str:
    max_words = max(int(scene.duration_seconds * words_per_minute / 60), 1)
    shots = "\n".join(
        f"    - Shot {shot.order + 1}: {shot.goal} ({shot.duration_seconds}s, {shot.framing})"
        for shot in scene.shots
    )
    role = _scene_role(scene)
    return (
        f"- Scene {scene.order + 1} ({role}): {scene.goal}\n"
        f"  Duration: {scene.duration_seconds}s\n"
        f"  Max voice words: {max_words}\n"
        f"  Camera shots:\n{shots}\n"
        f"  Source: {scene.source.section}, page {scene.source.page}, "
        f"paragraph {scene.source.paragraph}\n"
        f"  Source excerpts:\n{source_context}"
    )


def _scene_role(scene) -> str:
    if scene.id.endswith("-scene-intro"):
        return "opening title page"
    if scene.id.endswith("-scene-outro"):
        return "closing takeaway"
    return "content"
