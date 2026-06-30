"""Prompt templates for storyboard generation."""

from app.models.pipeline import ContentPlan
from app.models.section import Section
from app.services.screenshot_region_planner import ScreenshotRegionPlanner


def build_storyboard_prompt(
    content_plan: ContentPlan,
    *,
    max_scenes: int,
    max_video_duration_seconds: float,
    title_page_duration_seconds: float,
) -> str:
    """Build the Gemini prompt for planning a short-form video storyboard."""
    document = content_plan.document
    content_budget = max(max_video_duration_seconds - title_page_duration_seconds, 0)
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

    return f"""You are planning a short-form vertical video storyboard from a document.

Document title: {document.title or "Untitled"}

The finished video must be at most {max_video_duration_seconds:.0f} seconds total.
A title-page scene lasting about {title_page_duration_seconds:.0f} seconds is added automatically.
Plan only the remaining content scenes within roughly {content_budget:.0f} seconds.

Selected sections:
{sections}

Available paragraphs:
{paragraphs}

Create up to {max_scenes} content scenes that tell the full story within the time budget.
Plan structure only. Do not write voiceover or overlay text yet.

Return JSON with this exact shape:
{{
  "scenes": [
    {{
      "goal": "Introduce the paper",
      "duration_seconds": 6.0,
      "source": {{
        "section": "Introduction",
        "page": 1,
        "paragraph": 1
      }}
    }}
  ]
}}

Rules:
- Order scenes for a clear narrative arc: hook, evidence, takeaway.
- Cover the most important ideas from the selected sections within the time budget.
- source.section must match one of the selected section titles exactly.
- source.page and source.paragraph must refer to an available paragraph.
- duration_seconds must be between 3 and 8.
- The sum of all planned scene durations should stay within {content_budget:.0f} seconds.
- Return at most {max_scenes} scenes.
"""


def _format_section(section: Section, index: int) -> str:
    preview = section.content[:500] if section.content else "(no body text)"
    paragraphs = ", ".join(str(value) for value in section.paragraph_indices) or "unknown"
    return (
        f"{index}. {section.title} "
        f"(importance={section.importance_score:.2f}, paragraphs={paragraphs}): {preview}"
    )
