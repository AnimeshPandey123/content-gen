"""Prompt templates for script generation."""

from app.config import Settings, get_settings
from app.models.pipeline import StoryboardResult
from app.services.duration_budget import playback_duration
from app.services.source_context import (
    format_paper_brief,
    format_shot_source_context,
)

_AUDIENCE = (
    "Tech-literate viewers—software engineers, developers, and data scientists—"
    "who understand systems and APIs but do not read ML papers. They want to "
    "understand what the paper figured out and why it matters."
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
Paper brief (use intuition and meaning to teach—detail and source excerpts are for accuracy only):
{format_paper_brief(storyboard_result.content_plan.paper_brief)}

"""

    return f"""You are writing a short-form vertical video script from a storyboard.
Audience: {_AUDIENCE}

The script should sound like a clear tech explainer—informative and energetic, never
a paper recap. Be accurate to the paper; never invent facts or exaggerate results.

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
          "voice": "Today we're breaking down the Transformer—how Google ditched recurrence.",
          "overlay": "The Transformer"
        }},
        {{
          "shot_order": 1,
          "voice": "Old models read one word at a time, like proofreading letter by letter.",
          "overlay": "The Old Bottleneck"
        }}
      ]
    }}
  ]
}}

Rules:
- scene numbers must match the storyboard scene numbers exactly.
- Each scene must include exactly one script shot per storyboard shot listed for that scene.
- shot_order must match the storyboard shot order (0-based) exactly.
- Each shot voice must fit naturally within that shot's duration and target word count range.
- Each shot voice should match what the viewer sees in that shot—do not summarize
  the whole scene in one line.
- overlay: 2-5 words, intuitive labels readable on a phone—not paper jargon
  (e.g. "Best Translation Score" not "SOTA BLEU").
- Do not add extra scenes or shots.
- Do not include duration fields—timing comes from the storyboard.
- The opening scene is the automatic title-page intro. Shot 0 MUST name the paper
  (use Document title or its well-known name) in the first line—e.g. "Today we're
  breaking down AlphaGo Zero—how DeepMind taught Go with zero human games."
  Then add a hook question or surprising claim.
- The final scene is the automatic closing scene: the closing shot MUST (a) recap the key
  insight in one clause and (b) land the "so what" from the paper brief.
- The last content scene's final shot should hand off to the closing scene,
  not introduce new material.
- Middle scenes carry the argument; only the final scene's last shot should wrap up.

Intuition-first voiceover (do not narrate the paper):
- You are teaching ideas, not reading source text aloud. Source excerpts ground facts—
  never paraphrase them sentence-by-sentence into voice lines.
- Structure each shot: why it matters → intuition or analogy → optional precise number.
- Use the brief's intuition field and each evidence meaning as your narration guide.
- When introducing a technical idea, lead with a "think of it as..." or everyday analogy
  before the formal term (e.g. MCTS = "mentally plays thousands of future games before
  picking a move"—not "a tree search explores promising future states").
- Every technical concept must answer "why should I care?" before "what happened?"
- When citing a metric, name what it measures first (e.g. "translation quality score"
  before "28.4 BLEU").
- Cover the brief's key evidence; prioritize explaining the top 4–6 insights over listing
  every ablation row.
- Keep numbers accurate but always explain what they mean; never drop a number without
  its gloss.
- Introduce jargon once with a brief explanation or analogy, then reuse it naturally.

Anti-patterns (avoid paper mode):
- No narrating paper prose. Ban lines that sound like a textbook definition without
  an analogy (e.g. "explores promising future states" without explaining what that
  feels like to the viewer).
- No undefined acronyms (BLEU, F1, AP, MCTS) without a 3–5 word gloss on first use.
- No ablation numbers without stating what was removed and why that proves the design.
- Overlays: intuitive labels, not paper jargon ("Best Translation Score" not "SOTA BLEU").
- Do not use Big-O notation unless immediately explained in plain language
  (e.g. "work grows with the square of sentence length, often written as O(n²)"—not
  "requires O(n²) computation" alone).
- No paper-speak. Ban: "state-of-the-art", "novel architecture", "significantly
  outperforms", "we propose", "our method", "empirically demonstrate". Prefer:
  "best result at the time", "new design", "works better because", "the researchers
  built", "experiments showed".
- No unexplained proper nouns on first use. Name datasets and benchmarks with a brief
  gloss (e.g. "WMT14, a standard machine translation benchmark" not "WMT14" alone).

Tone and style:
- Sound like a YouTube explainer who makes ideas click—not a conference presenter.
- Use active voice and short sentences; must sound natural read aloud.
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
    min_words = max(int(max_words * 0.75), 1)
    visual = f', visual="{shot.visual}"' if shot.visual else ""
    source_context = format_shot_source_context(document, sections, scene, shot)
    return (
        f"    - Shot {shot.order + 1} (order={shot.order}): {shot.goal}\n"
        f"      Duration: {shot.duration_seconds}s | Target voice words: {min_words}–{max_words} | "
        f"Framing: {shot.framing}{visual}\n"
        f"      Source excerpts:\n{source_context}"
    )


def _scene_role(scene) -> str:
    if scene.id.endswith("-scene-intro"):
        return "opening title page"
    if scene.id.endswith("-scene-outro"):
        return "closing takeaway"
    return "content"
