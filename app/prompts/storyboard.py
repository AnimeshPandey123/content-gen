"""Prompt templates for storyboard generation."""

from app.models.pipeline import ContentPlan
from app.models.section import Section
from app.services.figure_detector import FigureDetector
from app.services.source_context import format_paper_brief
from app.services.screenshot_region_planner import ScreenshotRegionPlanner


def build_storyboard_prompt(content_plan: ContentPlan) -> str:
    """Build the Gemini prompt for planning a short-form video storyboard."""
    document = content_plan.document
    sections = "\n".join(
        _format_section(section, index)
        for index, section in enumerate(content_plan.selected_sections, start=1)
    )
    paragraphs = (
        "\n".join(
            f"- Paragraph {ref.index} (page {ref.page_number}): {ref.block.text[:300]}"
            for ref in ScreenshotRegionPlanner().iter_paragraphs(document)
        )
        or "- No paragraphs available"
    )
    visuals = _format_visual_catalog(document)
    brief_block = ""
    if content_plan.paper_brief is not None:
        brief_block = f"""
Paper brief (use this to plan a deep narrative—not surface summaries):
{format_paper_brief(content_plan.paper_brief)}
"""

    return f"""You are planning a short-form vertical video storyboard from a document.
The video should feel informative, visually appealing, and shareable—like a great science
explainer on TikTok, Reels, or Shorts. Stay credible: no clickbait, no invented claims.

Document title: {document.title or "Untitled"}
{brief_block}
Selected sections:
{sections}

Available paragraphs:
{paragraphs}

Detected figures and tables (ready to use—stronger storytellers than text crops):
{visuals}

The detected figures and tables above are already wired into the pipeline. When a shot
should show a diagram, chart, or results table, reference it with visual instead of cropping
paragraph text. Figures and tables usually communicate faster and more memorably than
wide/focus/highlight on body text.

You decide the pacing and structure: total runtime, title-page length, closing-scene length,
scene count, scene durations, and how many camera shots each scene needs.
A title-page scene on the first PDF page is added automatically using your title_page_duration_seconds.
A closing takeaway scene is added automatically at the end using your closing_scene_duration_seconds.
Plan content scenes only in the scenes array.

Plan structure only. Do not write voiceover or overlay text yet.

Return JSON with this exact shape:
{{
  "plan": {{
    "target_video_duration_seconds": 30.0,
    "title_page_duration_seconds": 4.0,
    "closing_scene_duration_seconds": 4.0,
    "min_scene_duration_seconds": 3.0
  }},
  "scenes": [
    {{
      "goal": "Explain the main result",
      "duration_seconds": 6.0,
      "source": {{
        "section": "Introduction",
        "page": 1,
        "paragraph": 1
      }},
      "shots": [
        {{
          "goal": "Show the full figure",
          "duration_seconds": 2.0,
          "page": 1,
          "paragraph": 1,
          "framing": "wide"
        }},
        {{
          "goal": "Zoom into the key graph",
          "duration_seconds": 2.5,
          "visual": "Figure 1"
        }}
      ]
    }}
  ]
}}

Rules:
- plan.target_video_duration_seconds is the total runtime including the title and closing scenes.
- plan.title_page_duration_seconds controls the automatic opening title-page scene.
- plan.closing_scene_duration_seconds controls the automatic closing takeaway scene.
- plan.min_scene_duration_seconds is the shortest scene you are willing to use.
- Order scenes for a clear narrative arc: hook, evidence, then build toward a takeaway.
  Do not plan a separate outro scene—the closing scene is added automatically.
- When a paper brief is provided, scene goals must reflect its mechanism and evidence—not generic labels.
- The last content scene should present evidence or results, not the final wrap-up narration.
- source.section must match one of the selected section titles exactly.
- source.page and source.paragraph must refer to an available paragraph.
- Content scene durations must be at least plan.min_scene_duration_seconds.
- Content scenes plus the title and closing scenes must fit within plan.target_video_duration_seconds.
- Decide how many content scenes and shots you need; use only as many as the story requires.
- Every scene must include a shots array with at least one entry.
- You choose each shot's goal and duration_seconds.
- For text shots, set page, paragraph, and framing.
- When a detected figure or table fits the story beat, use visual with its exact label
  (e.g. "Figure 1", "Table 2") instead of page/paragraph/framing—diagrams and tables
  are often the clearest way to show evidence.
- You do not have to use every detected visual; choose the ones that best serve the narrative.
- Shot duration_seconds values within a scene must sum to that scene's duration_seconds.
- Prefer wide framing for text. Avoid wide-then-focus on the same paragraph—it causes jarring
  jumps that clip headers and margins. Use focus only when moving to a different paragraph or page.
- When explaining architecture, results, or comparisons, check the detected list first—a
  figure or table shot is usually a better storyteller than zooming paragraph text.
- framing must be one of: wide, focus, highlight (only when visual is not set).
- wide = full page width, focus = full page width with a vertical band around the paragraph,
  highlight = a smaller band on the detail.

Creative direction (storyboard goals and shot goals):
- Hook fast: the first content scene should surface the paper's most surprising or valuable idea.
- Name what the viewer learns or feels in each scene goal—not just "show page 3".
- Plan visual payoff: when the detected list has a relevant figure or table, use it—visuals
  land faster than paragraphs of text on a phone screen.
- Build momentum: curiosity or tension early, evidence in the middle, strongest proof before the outro.
- Favor concrete claims (numbers, comparisons, state-of-the-art beats) over abstract methodology alone.
- Each shot goal should describe a visual beat (reveal, zoom, compare, highlight)—not filler transitions.
"""


def _format_visual_catalog(document) -> str:
    visuals = FigureDetector().detect_visuals(document)
    if not visuals:
        return "- No figures or tables detected"
    lines = []
    for visual in visuals:
        caption_text = (visual.caption or "").strip()
        if caption_text:
            caption_preview = caption_text.splitlines()[0][:120]
            detail = f": {caption_preview}"
        else:
            detail = ""
        lines.append(f"- {visual.label} (page {visual.page_number}, {visual.kind}){detail}")
    return "\n".join(lines)


def _format_section(section: Section, index: int) -> str:
    preview = section.content[:500] if section.content else "(no body text)"
    paragraphs = ", ".join(str(value) for value in section.paragraph_indices) or "unknown"
    return (
        f"{index}. {section.title} "
        f"(importance={section.importance_score:.2f}, paragraphs={paragraphs}): {preview}"
    )
