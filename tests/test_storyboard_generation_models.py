"""Unit tests for storyboard generation models."""

import pytest
from app.models.storyboard_generation import (
    PlannedScene,
    PlannedSceneSource,
    StoryboardGenerationResponse,
)
from pydantic import ValidationError


def test_planned_scene_requires_source() -> None:
    scene = PlannedScene(
        goal="Introduce the paper",
        duration_seconds=8.0,
        source=PlannedSceneSource(section="Introduction", page=1, paragraph=1),
    )
    assert scene.source.paragraph == 1


def test_planned_scene_duration_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        PlannedScene(
            goal="Hook",
            duration_seconds=0,
            source=PlannedSceneSource(section="Results", page=1, paragraph=1),
        )


def test_storyboard_generation_response_requires_scenes() -> None:
    with pytest.raises(ValidationError):
        StoryboardGenerationResponse(scenes=[])
