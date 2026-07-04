"""Prompt templates for paper brief generation."""

from app.models.pipeline import ContentPlan
from app.models.section import Section

_AUDIENCE = (
    "Tech-literate viewers—software engineers, developers, and data scientists—"
    "who understand systems and APIs but do not read ML papers. They want to "
    "understand what the paper figured out and why it matters, not reproduce "
    "the ablation section."
)


def build_paper_brief_prompt(content_plan: ContentPlan) -> str:
    """Build the Gemini prompt for synthesizing paper understanding."""
    document = content_plan.document
    sections = "\n\n".join(
        _format_section(section, index)
        for index, section in enumerate(content_plan.selected_sections, start=1)
    )

    return f"""You are analyzing a research paper to prepare a short-form video explainer.
Audience: {_AUDIENCE}

Read the selected sections carefully and extract deep, specific understanding—not surface
summaries. Translate paper jargon into plain language a CS grad would follow.

Document title: {document.title or "Untitled"}

Selected sections (full text):
{sections}

Return JSON with this exact shape:
{{
  "problem": "What problem or gap does this paper address?",
  "key_insight": "One plain-language sentence for the core idea.",
  "mechanism": "How the method works—cause and effect in 2–3 sentences, no notation.",
  "intuition": "One everyday analogy or mental model that makes the core idea click",
  "evidence": [
    {{
      "claim": "What was shown",
      "detail": "Exact number, baseline, dataset, or comparison from the text",
      "meaning": "Why it matters plus a plain analogy—speed, cost, quality, or 'think of it as...'",
      "source_section": "Section title"
    }}
  ],
  "limitations": "Main caveat or assumption stated or implied in the text",
  "so_what": "Practical impact: products, training cost, latency—not 'advances the field'"
}}

Rules:
- Ground every field in the section text above. Do not invent numbers or results.
- evidence must list 4–8 of the strongest, most specific points (metrics, ablations, SOTA beats).
- Capture every headline number in the text: speeds, accuracy metrics,
  dataset names, and baseline margins.
- For each evidence entry, meaning must explain why the viewer should care and include
  an intuition hook when helpful—not just restate the claim.
- When a claim comes from a table, include the exact figures and name the table or comparison.
- mechanism must be understandable without reading the paper—explain Big-O in plain
  language if used; gloss undefined acronyms and dataset names on first mention.
- Do not use paper-speak ("state-of-the-art", "we propose", "novel architecture") in
  any field—write like a tech explainer, not a conference abstract.
- intuition must be a concrete analogy a developer would repeat to a colleague
  (e.g. MCTS = "mentally plays thousands of future games before picking a move").
- Include tradeoffs and limitations explicitly—not just strengths.
- Prefer mechanism and tradeoffs over generic praise ("novel", "state-of-the-art" alone).
- If the paper compares to baselines, name them and the margin when available.
- Write for clarity: a script writer will use this to narrate a 60–120 second video.
"""


def _format_section(section: Section, index: int) -> str:
    body = section.content.strip() if section.content else "(no body text)"
    return f"### {index}. {section.title}\n{body}"
