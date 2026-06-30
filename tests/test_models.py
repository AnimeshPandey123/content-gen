"""Unit tests for Pydantic model validation and serialization."""

import json

import pytest
from app.models import (
    Document,
    DocumentMetadata,
    Page,
    PipelineInput,
    Scene,
    Script,
    ScriptScene,
    Section,
    Storyboard,
    VideoProject,
)
from app.models.bounding_box import BoundingBox
from app.models.scene import SceneShot
from app.models.caption import Caption
from app.models.scene import SceneSource, SceneVisual
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


def test_caption_accepts_valid_timing() -> None:
    caption = Caption(scene_id="s1", text="Hello", start_time=0.0, end_time=3.0)
    assert caption.end_time == 3.0


def test_scene_syncs_visual_to_first_shot() -> None:
    crop = BoundingBox(x=0, y=0, width=100, height=100)
    other_crop = BoundingBox(x=10, y=10, width=50, height=50)
    scene = Scene(
        id="sc-1",
        section_id="sec-1",
        order=0,
        goal="Intro scene",
        duration_seconds=3.0,
        source=SceneSource(section="Intro", page=1, paragraph=1),
        shots=[
            SceneShot(
                order=0,
                goal="Focus",
                duration_seconds=3.0,
                page=1,
                paragraph=1,
                framing="focus",
                crop=crop,
            ),
        ],
        visual=SceneVisual(page=1, crop=other_crop),
    )

    assert scene.visual.crop == crop


def test_scene_rejects_payload_without_visual_or_shots() -> None:
    with pytest.raises(ValidationError):
        Scene.model_validate(
            {
                "id": "sc-1",
                "section_id": "sec-1",
                "order": 0,
                "goal": "Intro scene",
                "duration_seconds": 3.0,
                "source": {"section": "Intro", "page": 1, "paragraph": 1},
            },
        )


def test_scene_legacy_validator_returns_non_dict_data_unchanged() -> None:
    scene = Scene.model_validate(
        {
            "id": "sc-1",
            "section_id": "sec-1",
            "order": 0,
            "goal": "Intro scene",
            "duration_seconds": 3.0,
            "source": {"section": "Intro", "page": 1, "paragraph": 1},
            "visual": {"page": 1, "crop": {"x": 0, "y": 0, "width": 100, "height": 100}},
        },
    )

    assert Scene._ensure_shots_from_legacy_visual(scene) is scene


def test_scene_model_validate_from_existing_instance() -> None:
    from tests.conftest import sample_scene

    scene = sample_scene()
    validated = Scene.model_validate(scene)

    assert validated.id == scene.id
    assert len(validated.shots) == 1


def test_scene_builds_shots_from_legacy_visual_payload() -> None:
    scene = Scene.model_validate(
        {
            "id": "sc-1",
            "section_id": "sec-1",
            "order": 0,
            "goal": "Intro scene",
            "duration_seconds": 3.0,
            "source": {"section": "Intro", "page": 1, "paragraph": 2},
            "visual": {"page": 1, "crop": {"x": 0, "y": 0, "width": 100, "height": 100}},
        },
    )

    assert len(scene.shots) == 1
    assert scene.shots[0].paragraph == 2


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
        goal="Intro scene",
        duration_seconds=3.0,
        source=SceneSource(section="Intro", page=1, paragraph=1),
        visual=SceneVisual(page=1, crop=BoundingBox(x=0, y=0, width=100, height=100)),
    )
    storyboard = Storyboard(document_id="doc-1", scenes=[scene])
    script = Script(
        scenes=[
            ScriptScene(
                scene=1,
                scene_id="sc-1",
                voice="Hello world",
                overlay="Hello",
                duration=3.0,
            ),
        ],
    )

    project = VideoProject(
        document=document,
        storyboard=storyboard,
        script=script,
    )

    payload = json.loads(project.model_dump_json())
    assert payload["document"]["id"] == "doc-1"
    assert payload["storyboard"]["scenes"][0]["goal"] == "Intro scene"
    assert payload["script"]["scenes"][0]["overlay"] == "Hello"
