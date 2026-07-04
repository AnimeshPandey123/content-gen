"""Unit tests for source context resolution."""

import pytest
from app.models.paper_brief import EvidencePoint, PaperBrief
from app.models.scene import SceneShot
from app.models.section import Section
from app.services.paper_brief_generator import PaperBriefGenerationError, PaperBriefGenerator
from app.services.source_context import (
    find_section,
    format_paper_brief,
    format_scene_source_context,
    format_shot_source_context,
)

from tests.conftest import sample_scene
from tests.test_figure_detector import _document_with_visuals
from tests.test_stages import _sample_document


def test_format_paper_brief_includes_evidence() -> None:
    brief = PaperBrief(
        problem="Problem",
        key_insight="Insight",
        mechanism="Mechanism",
        intuition="Like caching hot data instead of recomputing everything.",
        evidence=[
            EvidencePoint(
                claim="Better accuracy",
                detail="95% on ImageNet",
                meaning="Beats the previous best model by a wide margin on a standard benchmark",
                source_section="Results",
            ),
            EvidencePoint(
                claim="Another claim",
                detail="No section cited",
                meaning="Shows the approach generalizes beyond one dataset",
                source_section="",
            ),
        ],
        limitations="Small dataset",
        so_what="Matters for deployment",
    )

    formatted = format_paper_brief(brief)

    assert "95% on ImageNet" in formatted
    assert "Intuition:" in formatted
    assert "→ Beats the previous best model" in formatted
    assert "from Results" in formatted
    assert "Another claim: No section cited → Shows the approach" in formatted


def test_find_section_supports_partial_title_match() -> None:
    sections = [
        Section(id="sec-1", title="3 Results and Discussion", content="Body", page_numbers=[1]),
    ]

    matched = find_section(sections, "Results")

    assert matched is not None
    assert matched.title.startswith("3 Results")


def test_find_section_returns_none_when_missing() -> None:
    assert find_section([], "Missing") is None


def test_format_scene_source_context_includes_section_and_paragraph() -> None:
    document = _sample_document()
    sections = [
        Section(
            id="sec-1",
            title="Page 1",
            content="Section body with extra context.",
            page_numbers=[1],
            paragraph_indices=[1],
        ),
    ]
    scene = sample_scene(source={"section": "Page 1", "page": 1, "paragraph": 1})

    context = format_scene_source_context(document, sections, scene)

    assert "Section body with extra context." in context
    assert "Source paragraph 1" in context
    assert "Sample" in context


def test_format_scene_source_context_includes_visual_captions() -> None:
    document = _document_with_visuals()
    sections = [
        Section(
            id="sec-1",
            title="Results",
            content="See the figure and table.",
            page_numbers=[1],
            paragraph_indices=[1],
        ),
    ]
    scene = sample_scene(
        duration_seconds=6.0,
        source={"section": "Results", "page": 1, "paragraph": 1},
        shots=[
            SceneShot(
                order=0,
                goal="Show figure",
                duration_seconds=2.0,
                page=1,
                paragraph=1,
                visual="Figure 1",
                framing="wide",
                crop=document.pages[0].blocks[1].bbox,
            ),
            SceneShot(
                order=1,
                goal="Duplicate visual",
                duration_seconds=2.0,
                page=1,
                paragraph=1,
                visual="Figure 1",
                framing="focus",
                crop=document.pages[0].blocks[1].bbox,
            ),
            SceneShot(
                order=2,
                goal="Missing visual",
                duration_seconds=2.0,
                page=1,
                paragraph=1,
                visual="Figure 99",
                framing="focus",
                crop=document.pages[0].blocks[1].bbox,
            ),
        ],
    )

    context = format_scene_source_context(document, sections, scene)

    assert "Model architecture" in context
    assert "Figure 99: (caption not found)" in context
    assert context.count("- Figure 1 (page 1):") == 1


def test_format_scene_source_context_falls_back_when_nothing_resolves() -> None:
    document = _sample_document()
    scene = sample_scene(source={"section": "Missing", "page": 1, "paragraph": 99})

    context = format_scene_source_context(document, [], scene)

    assert context == "(no source text available)"


def test_format_shot_source_context_includes_visual_caption() -> None:
    document = _document_with_visuals()
    sections = [
        Section(
            id="sec-1",
            title="Results",
            content="See Figure 1.",
            page_numbers=[1],
            paragraph_indices=[1],
        ),
    ]
    scene = sample_scene(source={"section": "Results", "page": 1, "paragraph": 1})
    shot = scene.shots[0].model_copy(update={"visual": "Figure 1"})

    context = format_shot_source_context(document, sections, scene, shot)

    assert "Model architecture" in context


def test_format_shot_source_context_truncates_long_sections() -> None:
    document = _sample_document()
    sections = [
        Section(
            id="sec-1",
            title="Results",
            content="x" * 3100,
            page_numbers=[1],
            paragraph_indices=[1],
        ),
    ]
    scene = sample_scene(source={"section": "Results", "page": 1, "paragraph": 1})

    context = format_shot_source_context(document, sections, scene, scene.shots[0])

    assert "..." in context
    assert len(context) < 3200


def test_format_shot_source_context_handles_missing_paragraph_and_visual() -> None:
    document = _sample_document()
    scene = sample_scene(source={"section": "Missing", "page": 1, "paragraph": 99})
    shot = scene.shots[0].model_copy(update={"visual": "Figure 99"})

    context = format_shot_source_context(document, [], scene, shot)

    assert "Visual Figure 99: (caption not found)" in context


def test_generate_brief_wraps_gemini_errors() -> None:
    class _FailingClient:
        def generate_model(self, prompt, response_model):
            from app.agents.gemini_client import GeminiClientError

            raise GeminiClientError("boom")

    from app.models.pipeline import ContentPlan

    generator = PaperBriefGenerator(gemini_client=_FailingClient())
    content_plan = ContentPlan(
        document=_sample_document(),
        selected_sections=[
            Section(id="sec-1", title="T", content="Body", page_numbers=[1]),
        ],
    )

    with pytest.raises(PaperBriefGenerationError, match="boom"):
        generator.generate_brief(content_plan)
