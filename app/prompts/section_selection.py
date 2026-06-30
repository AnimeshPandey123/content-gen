"""Prompt templates for section selection."""

from app.services.document_sections import SectionCandidate


def build_section_selection_prompt(
    candidates: list[SectionCandidate],
    *,
    limit: int,
    document_title: str,
) -> str:
    """Build the Gemini prompt for ranking document sections."""
    catalog = "\n".join(
        f"- {index}. {candidate.title}: {candidate.content[:500]}"
        for index, candidate in enumerate(candidates, start=1)
    )
    return f"""You are selecting sections from a document for a short-form vertical video.

Document title: {document_title or "Untitled"}

Available sections:
{catalog}

Choose the top {limit} most interesting sections for a short video audience.
Prioritize results, findings, methods with clear takeaways, and compelling claims.
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
- Return at most {limit} sections.
- Order sections from most to least important.
"""
