"""Prompt templates for storyboard generation."""

from app.models.pipeline import ContentPlan
from app.models.section import Section
from app.services.figure_detector import FigureDetector
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

    return f"""You are planning a short-form vertical video storyboard from a document.

Document title: {document.title or "Untitled"}

Selected sections:
{sections}

Available paragraphs:
{paragraphs}

Detected figures and tables:
{visuals}

You decide the pacing and structure: total runtime, title-page length, scene count,
scene durations, and how many camera shots each scene needs.
A title-page scene on the first PDF page is added automatically using your title_page_duration_seconds.
Plan content scenes only in the scenes array.

Plan structure only. Do not write voiceover or overlay text yet.

Return JSON with this exact shape:
{{
  "plan": {{
    "target_video_duration_seconds": 30.0,
    "title_page_duration_seconds": 4.0,
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
- plan.target_video_duration_seconds is the total runtime including the title page.
- plan.title_page_duration_seconds controls the automatic opening title-page scene.
- plan.min_scene_duration_seconds is the shortest scene you are willing to use.
- Order scenes for a clear narrative arc: hook, evidence, takeaway.
- source.section must match one of the selected section titles exactly.
- source.page and source.paragraph must refer to an available paragraph.
- Content scene durations must be at least plan.min_scene_duration_seconds.
- Content scenes plus the title page must fit within plan.target_video_duration_seconds.
- Decide how many content scenes and shots you need; use only as many as the story requires.
- Every scene must include a shots array with at least one entry.
- You choose each shot's goal and duration_seconds.
- For text shots, set page, paragraph, and framing.
- For figure or table shots, set visual to an exact label from the detected list
  (e.g. "Figure 1", "Table 2") instead of page/paragraph/framing.
- Shot duration_seconds values within a scene must sum to that scene's duration_seconds.
- Prefer wide and focus framing for text. Use visual references for figures and tables.
- framing must be one of: wide, focus, highlight (only when visual is not set).
- wide = full page width, focus = full page width with a vertical band around the paragraph,
  highlight = a smaller band on the detail.
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
