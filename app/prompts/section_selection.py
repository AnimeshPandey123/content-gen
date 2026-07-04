"""Prompt templates for section selection."""

from app.services.document_sections import SectionCandidate

_AUDIENCE = (
    "Tech-literate viewers—software engineers, developers, and data scientists—"
    "who understand systems and APIs but do not read ML papers."
)


def build_section_selection_prompt(
    candidates: list[SectionCandidate],
    *,
    document_title: str,
) -> str:
    """Build the Gemini prompt for ranking document sections."""
    catalog = "\n".join(
        f"- {index}. {candidate.title}: {candidate.content[:1500]}"
        for index, candidate in enumerate(candidates, start=1)
    )
    return f"""You are selecting sections from a document for a short-form vertical video.
Audience: {_AUDIENCE}

The video should teach the paper's core idea and why it matters—not walk through
every experiment in the appendix.

Document title: {document_title or "Untitled"}

Available sections:
{catalog}

Choose the sections that best fit a compelling short video. Decide how many to include.
Prioritize abstract, introduction, main results, and conclusion—sections that support
a conceptual story with clear takeaways.
Favor sections with headline-worthy numbers, surprising ideas, or strong visual evidence
(figures, tables, benchmarks) that would make someone stop scrolling.
Deprioritize ablation studies, hyperparameter sensitivity, related work, and appendix
material unless they contain the paper's single clearest headline result.
Avoid boilerplate such as references, acknowledgements, and author lists.

Return JSON with this exact shape:
{{
  "sections": [
    {{"section": "Results", "importance": 0.95}}
  ]
}}

Rules:
- Use the section titles exactly as listed above.
- importance must be between 0 and 1.
- Include only sections that earn their place in a short video.
- Selected sections must support a conceptual story, not a methods appendix walkthrough.
- Order sections from most to least important.
"""
