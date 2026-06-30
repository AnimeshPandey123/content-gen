"""Unit tests for storyboard prompt building."""

from app.models.pipeline import ContentPlan
from app.models.section import Section
from app.prompts.storyboard import build_storyboard_prompt

from tests.test_stages import _sample_document


def test_build_storyboard_prompt_includes_sections_and_paragraphs() -> None:
    document = _sample_document()
    content_plan = ContentPlan(
        document=document,
        selected_sections=[
            Section(
                id="sec-1",
                title="Results",
                content="We achieved 95% accuracy.",
                page_numbers=[1],
                paragraph_indices=[1],
                importance_score=0.95,
            ),
        ],
    )

    prompt = build_storyboard_prompt(
        content_plan,
        max_scenes=3,
        max_video_duration_seconds=30.0,
        title_page_duration_seconds=4.0,
    )

    assert "Results" in prompt
    assert "Paragraph 1" in prompt
    assert "Return at most 3 scenes" in prompt
    assert "30 seconds" in prompt
    assert '"goal"' in prompt
    assert '"source"' in prompt
