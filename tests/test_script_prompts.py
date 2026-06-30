"""Unit tests for script prompt building."""

from app.models.pipeline import ContentPlan, StoryboardResult
from app.models.section import Section
from app.models.storyboard import Storyboard
from app.prompts.script import build_script_prompt

from tests.conftest import sample_scene
from tests.test_stages import _sample_document


def test_build_script_prompt_includes_storyboard_scenes() -> None:
    document = _sample_document()
    storyboard_result = StoryboardResult(
        content_plan=ContentPlan(
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
        ),
        storyboard=Storyboard(
            document_id=document.id,
            scenes=[sample_scene(goal="Introduce the finding")],
        ),
    )

    prompt = build_script_prompt(storyboard_result)

    assert "Introduce the finding" in prompt
    assert '"voice"' in prompt
    assert '"overlay"' in prompt
