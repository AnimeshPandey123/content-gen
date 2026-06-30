"""Unit tests for storyboard generation models."""

import pytest
from app.models.storyboard_generation import PlannedScene, StoryboardGenerationResponse
from pydantic import ValidationError


def test_planned_scene_requires_all_fields() -> None:
    scene = PlannedScene(
        goal="Hook the viewer",
        duration_seconds=6.0,
        source="Results",
        screenshot="Paragraph with the main finding",
        paragraph_index=2,
        narration="We achieved ninety-five percent accuracy.",
        caption="95% accuracy",
    )
    assert scene.goal == "Hook the viewer"


def test_planned_scene_duration_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        PlannedScene(
            goal="Hook",
            duration_seconds=0,
            source="Results",
            screenshot="Paragraph 1",
            paragraph_index=1,
            narration="Narration",
            caption="Caption",
        )


def test_storyboard_generation_response_requires_scenes() -> None:
    with pytest.raises(ValidationError):
        StoryboardGenerationResponse(scenes=[])
