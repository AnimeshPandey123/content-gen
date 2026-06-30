"""Unit tests for paper brief prompt building."""

from app.models.pipeline import ContentPlan
from app.models.section import Section
from app.prompts.paper_brief import build_paper_brief_prompt

from tests.test_stages import _sample_document


def test_build_paper_brief_prompt_includes_full_section_text() -> None:
    document = _sample_document()
    content_plan = ContentPlan(
        document=document,
        selected_sections=[
            Section(
                id="sec-1",
                title="Results",
                content="Accuracy reached 95% on ImageNet, beating ResNet by 3 points.",
                page_numbers=[1],
                paragraph_indices=[1],
                importance_score=0.95,
            ),
        ],
    )

    prompt = build_paper_brief_prompt(content_plan)

    assert "Results" in prompt
    assert "95% on ImageNet" in prompt
    assert '"mechanism"' in prompt
    assert "Do not invent numbers" in prompt
