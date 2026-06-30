"""Unit tests for script generation response models."""

import pytest
from app.models.script_generation import GeneratedScriptScene, ScriptGenerationResponse
from pydantic import ValidationError


def test_generated_script_scene_requires_fields() -> None:
    scene = GeneratedScriptScene(
        scene=1,
        voice="Voice line",
        overlay="Overlay",
        duration=8.0,
    )
    assert scene.scene == 1


def test_script_generation_response_requires_scenes() -> None:
    with pytest.raises(ValidationError):
        ScriptGenerationResponse(scenes=[])
