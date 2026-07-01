"""Unit tests for script prompt building."""

from app.models.paper_brief import PaperBrief
from app.models.pipeline import ContentPlan, StoryboardResult
from app.models.scene import SceneSource
from app.models.section import Section
from app.models.storyboard import Storyboard
from app.prompts.script import build_script_prompt

from tests.conftest import sample_scene, sample_video_plan
from tests.conftest import sample_brief_response
from tests.test_stages import _sample_document


def test_build_script_prompt_includes_storyboard_scenes() -> None:
    document = _sample_document()
    brief = PaperBrief.model_validate(sample_brief_response().model_dump())
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
            paper_brief=brief,
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
                    source=SceneSource(section="Results", page=1, paragraph=1),
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
    assert "Paper brief" in prompt
    assert "Source excerpts" in prompt
    assert "95% accuracy" in prompt
    assert "concrete facts" in prompt
    assert "shot_order" in prompt
    assert "Do not include duration" in prompt
    assert "one script entry per storyboard shot" in prompt
    assert '"voice"' in prompt
    assert '"overlay"' in prompt
