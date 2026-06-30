"""Unit tests for Gemini-backed storyboard generation."""

import pytest
from app.models.pipeline import ContentPlan
from app.models.section import Section
from app.models.storyboard_generation import (
    PlannedScene,
    PlannedSceneSource,
    StoryboardGenerationResponse,
)
from app.services.storyboard_generator import (
    StoryboardGenerationError,
    StoryboardGenerator,
    _match_section,
)

from tests.test_stages import _sample_document


class _FakeGeminiClient:
    def __init__(self, response: StoryboardGenerationResponse) -> None:
        self._response = response
        self.prompts: list[str] = []

    def generate_model(self, prompt: str, response_model):
        self.prompts.append(prompt)
        return self._response


def _content_plan() -> ContentPlan:
    return ContentPlan(
        document=_sample_document(),
        selected_sections=[
            Section(
                id="sec-1",
                title="Page 1",
                content="Sample",
                page_numbers=[1],
                paragraph_indices=[1],
                importance_score=0.9,
            ),
        ],
    )


def test_plan_scenes_returns_llm_output() -> None:
    fake_client = _FakeGeminiClient(
        StoryboardGenerationResponse(
            scenes=[
                PlannedScene(
                    goal="Introduce the sample",
                    duration_seconds=5.0,
                    source=PlannedSceneSource(section="Page 1", page=1, paragraph=1),
                ),
            ],
        ),
    )
    generator = StoryboardGenerator(gemini_client=fake_client)

    scenes = generator.plan_scenes(_content_plan())

    assert scenes[0].goal == "Introduce the sample"
    assert "Page 1" in fake_client.prompts[0]


def test_generate_storyboard_builds_scene_models() -> None:
    fake_client = _FakeGeminiClient(
        StoryboardGenerationResponse(
            scenes=[
                PlannedScene(
                    goal="Introduce the sample",
                    duration_seconds=5.0,
                    source=PlannedSceneSource(section="Page 1", page=1, paragraph=1),
                ),
            ],
        ),
    )
    generator = StoryboardGenerator(gemini_client=fake_client)

    storyboard = generator.generate_storyboard(_content_plan())

    assert len(storyboard.scenes) == 1
    scene = storyboard.scenes[0]
    assert scene.goal == "Introduce the sample"
    assert scene.source.paragraph == 1
    assert scene.visual.crop.width > 0


def test_generate_storyboard_requires_api_key_when_client_not_injected() -> None:
    from app.config import Settings

    generator = StoryboardGenerator(settings=Settings(gemini_api_key=None))

    with pytest.raises(StoryboardGenerationError, match="GEMINI_API_KEY"):
        generator.generate_storyboard(_content_plan())


def test_plan_scenes_wraps_gemini_errors() -> None:
    class _BadClient:
        def generate_model(self, prompt, response_model):
            from app.agents.gemini_client import GeminiClientError

            raise GeminiClientError("boom")

    generator = StoryboardGenerator(gemini_client=_BadClient())

    with pytest.raises(StoryboardGenerationError, match="boom"):
        generator.plan_scenes(_content_plan())


def test_build_client_uses_settings_api_key(monkeypatch) -> None:
    from app.config import Settings

    created: list[str] = []

    class _RecordingClient:
        def __init__(self, *, api_key: str, model: str) -> None:
            created.append(api_key)

        def generate_model(self, prompt, response_model):
            return StoryboardGenerationResponse(
                scenes=[
                    PlannedScene(
                        goal="Hook",
                        duration_seconds=5.0,
                        source=PlannedSceneSource(section="Page 1", page=1, paragraph=1),
                    ),
                ],
            )

    monkeypatch.setattr(
        "app.services.storyboard_generator.GeminiClient",
        lambda **kwargs: _RecordingClient(**kwargs),
    )
    generator = StoryboardGenerator(settings=Settings(gemini_api_key="secret-key"))
    generator.plan_scenes(_content_plan())
    assert created == ["secret-key"]


def test_generate_storyboard_raises_when_llm_returns_unknown_sections() -> None:
    fake_client = _FakeGeminiClient(
        StoryboardGenerationResponse(
            scenes=[
                PlannedScene(
                    goal="Hook",
                    duration_seconds=5.0,
                    source=PlannedSceneSource(section="Conclusion", page=1, paragraph=1),
                ),
            ],
        ),
    )
    generator = StoryboardGenerator(gemini_client=fake_client)

    with pytest.raises(StoryboardGenerationError, match="No scenes matched"):
        generator.generate_storyboard(_content_plan())


def test_generate_storyboard_skips_invalid_paragraph_index() -> None:
    fake_client = _FakeGeminiClient(
        StoryboardGenerationResponse(
            scenes=[
                PlannedScene(
                    goal="Hook",
                    duration_seconds=5.0,
                    source=PlannedSceneSource(section="Page 1", page=1, paragraph=99),
                ),
            ],
        ),
    )
    generator = StoryboardGenerator(gemini_client=fake_client)

    with pytest.raises(StoryboardGenerationError, match="No scenes matched"):
        generator.generate_storyboard(_content_plan())


def test_match_section_supports_partial_title_match() -> None:
    sections = [
        Section(
            id="sec-1",
            title="Results and Discussion",
            content="Body",
            page_numbers=[1],
        ),
    ]
    matched = _match_section(sections, "Results")
    assert matched is not None
    assert matched.title == "Results and Discussion"
