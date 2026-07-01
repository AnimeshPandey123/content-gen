"""Unit tests for Gemini-backed script generation."""

import pytest
from app.models.pipeline import ContentPlan, StoryboardResult
from app.models.script_generation import (
    GeneratedScriptScene,
    GeneratedScriptShot,
    ScriptGenerationResponse,
)
from app.models.section import Section
from app.models.storyboard import Storyboard
from app.services.script_generator import ScriptGenerationError, ScriptGenerator

from tests.conftest import sample_scene
from tests.test_stages import _sample_document


class _FakeGeminiClient:
    def __init__(self, response: ScriptGenerationResponse) -> None:
        self._response = response
        self.prompts: list[str] = []

    def generate_model(self, prompt: str, response_model):
        self.prompts.append(prompt)
        return self._response


def _script_response(*, scene: int = 1, shot_count: int = 1) -> ScriptGenerationResponse:
    return ScriptGenerationResponse(
        scenes=[
            GeneratedScriptScene(
                scene=scene,
                shots=[
                    GeneratedScriptShot(
                        shot_order=index,
                        voice=f"Voice for shot {index + 1}",
                        overlay=f"Overlay {index + 1}",
                    )
                    for index in range(shot_count)
                ],
            ),
        ],
    )


def _storyboard_result(*, shot_count: int = 1) -> StoryboardResult:
    document = _sample_document()
    return StoryboardResult(
        content_plan=ContentPlan(
            document=document,
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
        ),
        storyboard=Storyboard(
            document_id=document.id,
            scenes=[sample_scene(id="doc-test-scene-1", duration_seconds=8.0)],
        ),
    )


def test_generate_scenes_returns_llm_output() -> None:
    fake_client = _FakeGeminiClient(_script_response())
    generator = ScriptGenerator(gemini_client=fake_client)

    scenes = generator.generate_scenes(_storyboard_result())

    assert scenes[0].shots[0].voice.startswith("Voice for shot")
    assert "Shot 1" in fake_client.prompts[0]
    assert "shot_order" in fake_client.prompts[0]


def test_generate_script_builds_script_model() -> None:
    fake_client = _FakeGeminiClient(_script_response())
    generator = ScriptGenerator(gemini_client=fake_client)

    script = generator.generate_script(_storyboard_result())

    assert len(script.scenes) == 1
    assert script.scenes[0].scene_id == "doc-test-scene-1"
    assert script.scenes[0].shots[0].overlay == "Overlay 1"
    assert script.scenes[0].voice == "Voice for shot 1"


def test_generate_script_requires_api_key_when_client_not_injected() -> None:
    from app.config import Settings

    generator = ScriptGenerator(settings=Settings(gemini_api_key=None))

    with pytest.raises(ScriptGenerationError, match="GEMINI_API_KEY"):
        generator.generate_script(_storyboard_result())


def test_generate_scenes_wraps_gemini_errors() -> None:
    class _BadClient:
        def generate_model(self, prompt, response_model):
            from app.agents.gemini_client import GeminiClientError

            raise GeminiClientError("boom")

    generator = ScriptGenerator(gemini_client=_BadClient())

    with pytest.raises(ScriptGenerationError, match="boom"):
        generator.generate_scenes(_storyboard_result())


def test_build_client_uses_settings_api_key(monkeypatch) -> None:
    from app.config import Settings

    created: list[str] = []

    class _RecordingClient:
        def __init__(self, *, api_key: str, model: str) -> None:
            created.append(api_key)

        def generate_model(self, prompt, response_model):
            return _script_response()

    monkeypatch.setattr(
        "app.services.script_generator.GeminiClient",
        lambda **kwargs: _RecordingClient(**kwargs),
    )
    generator = ScriptGenerator(settings=Settings(gemini_api_key="secret-key"))
    generator.generate_scenes(_storyboard_result())
    assert created == ["secret-key"]


def test_generate_script_builds_multi_shot_scene() -> None:
    from app.models.bounding_box import BoundingBox
    from app.models.scene import SceneShot

    document = _sample_document()
    crop = BoundingBox(x=72.0, y=72.0, width=400.0, height=18.0)
    storyboard_result = StoryboardResult(
        content_plan=ContentPlan(
            document=document,
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
        ),
        storyboard=Storyboard(
            document_id=document.id,
            scenes=[
                sample_scene(
                    id="doc-test-scene-1",
                    duration_seconds=8.0,
                    shots=[
                        SceneShot(
                            order=0,
                            goal="Wide",
                            duration_seconds=3.2,
                            page=1,
                            paragraph=1,
                            framing="wide",
                            crop=crop,
                        ),
                        SceneShot(
                            order=1,
                            goal="Focus",
                            duration_seconds=4.8,
                            page=1,
                            paragraph=1,
                            framing="focus",
                            crop=crop,
                        ),
                    ],
                ),
            ],
        ),
    )
    fake_client = _FakeGeminiClient(_script_response(shot_count=2))
    generator = ScriptGenerator(gemini_client=fake_client)

    script = generator.generate_script(storyboard_result)

    assert len(script.scenes[0].shots) == 2
    assert script.scenes[0].voice == "Voice for shot 1 Voice for shot 2"


def test_generate_script_raises_when_scene_numbers_do_not_match() -> None:
    fake_client = _FakeGeminiClient(_script_response(scene=9))
    generator = ScriptGenerator(gemini_client=fake_client)

    with pytest.raises(ScriptGenerationError, match="No script scenes matched"):
        generator.generate_script(_storyboard_result())


def test_generate_script_raises_when_shot_count_mismatches() -> None:
    fake_client = _FakeGeminiClient(_script_response(shot_count=2))
    generator = ScriptGenerator(gemini_client=fake_client)

    with pytest.raises(ScriptGenerationError, match="expected 1"):
        generator.generate_script(_storyboard_result())


def test_generate_script_raises_when_shot_order_missing() -> None:
    fake_client = _FakeGeminiClient(
        ScriptGenerationResponse(
            scenes=[
                GeneratedScriptScene(
                    scene=1,
                    shots=[
                        GeneratedScriptShot(
                            shot_order=1,
                            voice="Second only",
                            overlay="Second",
                        ),
                    ],
                ),
            ],
        ),
    )
    generator = ScriptGenerator(gemini_client=fake_client)

    with pytest.raises(ScriptGenerationError, match="missing script for shot_order 0"):
        generator.generate_script(_storyboard_result())
