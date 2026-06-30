"""Prompt templates for paper brief generation."""

from app.models.pipeline import ContentPlan
from app.models.section import Section


def build_paper_brief_prompt(content_plan: ContentPlan) -> str:
    """Build the Gemini prompt for synthesizing paper understanding."""
    document = content_plan.document
    sections = "\n\n".join(
        _format_section(section, index)
        for index, section in enumerate(content_plan.selected_sections, start=1)
    )

    return f"""You are analyzing a research paper to prepare a short-form video explainer.
Read the selected sections carefully and extract deep, specific understanding—not surface summaries.

Document title: {document.title or "Untitled"}

Selected sections (full text):
{sections}

Return JSON with this exact shape:
{{
  "problem": "What problem or gap does this paper address?",
  "key_insight": "One plain-language sentence for the core idea.",
  "mechanism": "How the method works—cause and effect, not buzzwords.",
  "evidence": [
    {{
      "claim": "What was shown",
      "detail": "Exact number, baseline, dataset, or comparison from the text",
      "source_section": "Section title"
    }}
  ],
  "limitations": "Main caveat or assumption stated or implied in the text",
  "so_what": "Why a smart non-expert should care"
}}

Rules:
- Ground every field in the section text above. Do not invent numbers or results.
- evidence must list 2–5 of the strongest, most specific points (metrics, ablations, SOTA beats).
- Prefer mechanism and tradeoffs over generic praise ("novel", "state-of-the-art" alone).
- If the paper compares to baselines, name them and the margin when available.
- Write for clarity: a script writer will use this to narrate a 30–90 second video.
"""


def _format_section(section: Section, index: int) -> str:
    body = section.content.strip() if section.content else "(no body text)"
    return f"### {index}. {section.title}\n{body}"
