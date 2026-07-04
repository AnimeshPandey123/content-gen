"""Unit tests for storyboard generation models."""

import pytest
from app.models.storyboard_generation import (
    PlannedScene,
    PlannedSceneSource,
    PlannedShot,
    StoryboardGenerationResponse,
)
from pydantic import ValidationError

from tests.conftest import sample_planned_shots, sample_video_plan


def test_planned_scene_requires_source() -> None:
    scene = PlannedScene(
        goal="Introduce the paper",
        duration_seconds=8.0,
        source=PlannedSceneSource(section="Introduction", page=1, paragraph=1),
        shots=sample_planned_shots(duration=8.0),
    )
    assert scene.source.paragraph == 1


def test_planned_scene_requires_shots() -> None:
    with pytest.raises(ValidationError):
        PlannedScene(
            goal="Introduce the paper",
            duration_seconds=8.0,
            source=PlannedSceneSource(section="Introduction", page=1, paragraph=1),
        )


def test_planned_scene_duration_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        PlannedScene(
            goal="Hook",
            duration_seconds=0,
            source=PlannedSceneSource(section="Results", page=1, paragraph=1),
            shots=sample_planned_shots(),
        )


def test_planned_shot_requires_framing() -> None:
    with pytest.raises(ValidationError):
        PlannedShot(
            goal="Zoom the graph",
            duration_seconds=2.0,
            page=1,
            paragraph=1,
        )


def test_planned_shot_accepts_framing() -> None:
    shot = PlannedShot(
        goal="Zoom the graph",
        duration_seconds=2.0,
        page=1,
        paragraph=1,
        framing="highlight",
    )
    assert shot.framing == "highlight"


def test_planned_shot_accepts_visual_reference() -> None:
    shot = PlannedShot(
        goal="Show the architecture diagram",
        duration_seconds=2.0,
        visual="Figure 3",
    )
    assert shot.visual == "Figure 3"
    assert shot.page is None


def test_planned_shot_requires_visual_or_framing_fields() -> None:
    with pytest.raises(ValidationError, match="Either visual or page"):
        PlannedShot(
            goal="Missing targeting",
            duration_seconds=2.0,
            page=1,
            paragraph=1,
        )


def test_planned_shot_accepts_marker_highlight() -> None:
    shot = PlannedShot(
        goal="Call out the key result",
        duration_seconds=2.0,
        page=1,
        paragraph=1,
        framing="focus",
        marker_highlight=True,
    )
    assert shot.marker_highlight is True


def test_storyboard_generation_response_requires_scenes() -> None:
    with pytest.raises(ValidationError):
        StoryboardGenerationResponse(plan=sample_video_plan(), scenes=[])
