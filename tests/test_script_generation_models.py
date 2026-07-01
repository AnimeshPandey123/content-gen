"""Unit tests for script generation response models."""

import pytest
from app.models.script_generation import (
    GeneratedScriptScene,
    GeneratedScriptShot,
    ScriptGenerationResponse,
)
from pydantic import ValidationError


def test_generated_script_shot_requires_fields() -> None:
    shot = GeneratedScriptShot(
        shot_order=0,
        voice="Voice line",
        overlay="Overlay",
    )
    assert shot.shot_order == 0


def test_generated_script_scene_requires_shots() -> None:
    scene = GeneratedScriptScene(
        scene=1,
        shots=[
            GeneratedScriptShot(shot_order=0, voice="Voice", overlay="Overlay"),
        ],
    )
    assert scene.scene == 1


def test_script_generation_response_requires_scenes() -> None:
    with pytest.raises(ValidationError):
        ScriptGenerationResponse(scenes=[])
