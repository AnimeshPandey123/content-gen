"""Unit tests for storyboard prompt building."""

from app.models.paper_brief import PaperBrief
from app.models.pipeline import ContentPlan
from app.models.section import Section
from app.prompts.storyboard import _format_visual_catalog, build_storyboard_prompt

from tests.conftest import sample_brief_response
from tests.test_figure_detector import _document_with_visuals
from tests.test_stages import _sample_document


def test_build_storyboard_prompt_lets_llm_decide_structure() -> None:
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

    prompt = build_storyboard_prompt(content_plan)

    assert "Results" in prompt
    assert "Paragraph 1" in prompt
    assert '"plan"' in prompt
    assert "target_video_duration_seconds" in prompt
    assert "title_page_duration_seconds" in prompt
    assert "closing_scene_duration_seconds" in prompt
    assert "min_scene_duration_seconds" in prompt
    assert '"shots"' in prompt
    assert "Detected figures and tables" in prompt
    assert "stronger storytellers" in prompt
    assert "ready to use" in prompt
    assert "Decide how many content scenes" in prompt
    assert "between 60 and 120 seconds" in prompt
    assert "tech-literate" in prompt.lower()
    assert "What intuition will the viewer have" in prompt
    assert "at most one" in prompt
    assert "Creative direction" in prompt
    assert "Return at most" not in prompt
    assert "marker_highlight" in prompt
    assert "Use sparingly" in prompt


def test_build_storyboard_prompt_includes_paper_brief_when_present() -> None:
    document = _sample_document()
    brief = PaperBrief.model_validate(sample_brief_response().model_dump())
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
        paper_brief=brief,
    )

    prompt = build_storyboard_prompt(content_plan)

    assert "Paper brief" in prompt
    assert brief.key_insight in prompt
    assert "reflect its mechanism" in prompt


def test_format_visual_catalog_lists_detected_visuals() -> None:
    catalog = _format_visual_catalog(_document_with_visuals())
    assert "Figure 1" in catalog
    assert "Table 1" in catalog


def test_format_visual_catalog_handles_empty_document() -> None:
    assert _format_visual_catalog(_sample_document()) == "- No figures or tables detected"


def test_format_visual_catalog_handles_blank_caption() -> None:
    from app.models.blocks import Caption, Figure
    from app.models.bounding_box import BoundingBox
    from app.models.document import Document
    from app.models.metadata import DocumentMetadata
    from app.models.page import Page

    document = Document(
        id="doc-blank-caption",
        source_path="/tmp/blank.pdf",
        metadata=DocumentMetadata(page_count=1),
        pages=[
            Page(
                page_number=1,
                text="",
                width=612,
                height=792,
                blocks=[
                    Figure(
                        id="f1",
                        order=0,
                        bbox=BoundingBox(x=72, y=150, width=200, height=100),
                    ),
                    Caption(id="c1", order=1, text="   ", target_id="f1"),
                ],
            ),
        ],
    )

    catalog = _format_visual_catalog(document)

    assert catalog == "- Figure 1 (page 1, figure)"
