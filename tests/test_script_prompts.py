"""Unit tests for script prompt building."""

from app.models.pipeline import ContentPlan, StoryboardResult
from app.models.section import Section
from app.models.storyboard import Storyboard
from app.prompts.script import build_script_prompt

from tests.conftest import sample_scene, sample_video_plan
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
            scenes=[
                sample_scene(
                    id=f"{document.id}-scene-intro",
                    order=0,
                    goal="Show the paper title page",
                ),
                sample_scene(
                    id="scene-1",
                    order=1,
                    goal="Introduce the finding",
                ),
                sample_scene(
                    id=f"{document.id}-scene-outro",
                    order=2,
                    goal="Conclude with the paper's main takeaway",
                ),
            ],
            plan=sample_video_plan(target_video_duration_seconds=30.0),
        ),
    )

    prompt = build_script_prompt(storyboard_result)

    assert "Introduce the finding" in prompt
    assert "opening title page" in prompt
    assert "closing takeaway" in prompt
    assert "Tone and style" in prompt
    assert "shareable" in prompt
    assert '"voice"' in prompt
    assert '"overlay"' in prompt
