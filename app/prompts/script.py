"""Prompt templates for script generation."""

from app.config import Settings, get_settings
from app.models.pipeline import StoryboardResult
from app.services.duration_budget import playback_duration
from app.services.source_context import (
    format_paper_brief,
    format_shot_source_context,
)


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
            document=document,
            sections=sections,
            words_per_minute=settings.words_per_minute,
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

Write one script entry per storyboard shot (not per scene).
Return JSON with this exact shape:
{{
  "scenes": [
    {{
      "scene": 1,
      "shots": [
        {{
          "shot_order": 0,
          "voice": "Here's the overall Transformer architecture.",
          "overlay": "Transformer"
        }},
        {{
          "shot_order": 1,
          "voice": "Multi-head attention links every word in parallel.",
          "overlay": "Multi-Head Attention"
        }}
      ]
    }}
  ]
}}

Rules:
- scene numbers must match the storyboard scene numbers exactly.
- Each scene must include exactly one script shot per storyboard shot listed for that scene.
- shot_order must match the storyboard shot order (0-based) exactly.
- Each shot voice must fit naturally within that shot's duration and max word count.
- Each shot voice should match what the viewer sees in that shot—do not summarize the whole scene in one line.
- overlay: 2-5 words, punchy and readable on a phone; tease the insight for that shot only.
- Do not add extra scenes or shots.
- Do not include duration fields—timing comes from the storyboard.
- The opening scene is the automatic title-page intro: write a hook or teaser for shot 0.
- The final scene is the automatic closing scene: the last shot MUST conclude with a clear
  takeaway or "so what"—do not end on raw results or unfinished technical detail.
- Middle scenes carry the argument; only the final scene's last shot should wrap up.
- Each shot includes Source excerpts—voice MUST use concrete facts from those excerpts when relevant.
- Prefer mechanism, numbers, and comparisons over vague praise (avoid "novel approach" without specifics).

Tone and style:
- Open with a hook: a question, bold claim, or surprising fact—never "In this paper" or "The authors".
- Use active voice and short sentences; must sound natural read aloud.
- Explain jargon in plain language; prefer specific numbers and comparisons over vague praise.
- Avoid academic filler: "we propose", "it is shown that", "in this work", "the following".
- Virality comes from a genuinely interesting insight told clearly—not hype, caps lock, or empty superlatives.
"""


def _format_scene(scene, *, document, sections, words_per_minute: int) -> str:
    role = _scene_role(scene)
    shot_blocks = "\n".join(
        _format_shot(
            scene,
            shot,
            document=document,
            sections=sections,
            words_per_minute=words_per_minute,
        )
        for shot in scene.shots
    )
    return (
        f"- Scene {scene.order + 1} ({role}): {scene.goal}\n"
        f"  Duration: {scene.duration_seconds}s\n"
        f"  Source: {scene.source.section}, page {scene.source.page}, "
        f"paragraph {scene.source.paragraph}\n"
        f"  Shots:\n{shot_blocks}"
    )


def _format_shot(scene, shot, *, document, sections, words_per_minute: int) -> str:
    max_words = max(int(shot.duration_seconds * words_per_minute / 60), 1)
    visual = f', visual="{shot.visual}"' if shot.visual else ""
    source_context = format_shot_source_context(document, sections, scene, shot)
    return (
        f"    - Shot {shot.order + 1} (order={shot.order}): {shot.goal}\n"
        f"      Duration: {shot.duration_seconds}s | Max voice words: {max_words} | "
        f"Framing: {shot.framing}{visual}\n"
        f"      Source excerpts:\n{source_context}"
    )


def _scene_role(scene) -> str:
    if scene.id.endswith("-scene-intro"):
        return "opening title page"
    if scene.id.endswith("-scene-outro"):
        return "closing takeaway"
    return "content"
