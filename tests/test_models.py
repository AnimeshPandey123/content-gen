"""Unit tests for Pydantic model validation and serialization."""

import json

import pytest
from app.models import (
    Caption,
    Document,
    DocumentMetadata,
    Narration,
    Page,
    PipelineInput,
    Scene,
    ScreenshotRegion,
    Section,
    Storyboard,
    VideoProject,
)
from pydantic import ValidationError


def test_pipeline_input_requires_pdf_path() -> None:
    with pytest.raises(ValidationError):
        PipelineInput(pdf_path="")


def test_page_page_number_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Page(page_number=0)


def test_section_requires_page_numbers() -> None:
    with pytest.raises(ValidationError):
        Section(id="s1", title="T", content="C", page_numbers=[])


def test_caption_end_time_must_exceed_start_time() -> None:
    with pytest.raises(ValidationError):
        Caption(scene_id="s1", text="Hello", start_time=5.0, end_time=3.0)


def test_screenshot_region_requires_positive_dimensions() -> None:
    with pytest.raises(ValidationError):
        ScreenshotRegion(scene_id="s1", page_number=1, x=0, y=0, width=0, height=100)


def test_models_serialize_to_json() -> None:
    document = Document(
        id="doc-1",
        source_path="/tmp/sample.pdf",
        metadata=DocumentMetadata(page_count=1),
        pages=[Page(page_number=1, text="Hello")],
        sections=[
            Section(id="sec-1", title="Intro", content="Hello", page_numbers=[1]),
        ],
    )
    scene = Scene(
        id="sc-1",
        section_id="sec-1",
        order=0,
        description="Intro scene",
        duration_seconds=3.0,
    )
    storyboard = Storyboard(document_id="doc-1", scenes=[scene])
    region = ScreenshotRegion(scene_id="sc-1", page_number=1, x=0, y=0, width=100, height=100)
    narration = Narration(scene_id="sc-1", text="Hello world", estimated_duration_seconds=3.0)
    caption = Caption(scene_id="sc-1", text="Hello world", start_time=0.0, end_time=3.0)

    project = VideoProject(
        document=document,
        storyboard=storyboard,
        screenshot_regions=[region],
        narrations=[narration],
        captions=[caption],
    )

    payload = json.loads(project.model_dump_json())
    assert payload["document"]["id"] == "doc-1"
    assert payload["document"]["raw_text"] == "Hello"
    assert payload["storyboard"]["scenes"][0]["id"] == "sc-1"
    assert payload["captions"][0]["text"] == "Hello world"
