"""Unit tests for script models."""

import pytest
from app.models.script import Script, ScriptScene
from pydantic import ValidationError


def test_script_scene_requires_voice_and_overlay() -> None:
    scene = ScriptScene(
        scene=1,
        scene_id="scene-1",
        voice="This paper proposes a new training method.",
        overlay="Train with Less Data",
        duration=8.0,
    )
    assert scene.overlay == "Train with Less Data"


def test_script_requires_scenes() -> None:
    with pytest.raises(ValidationError):
        Script(scenes=[])
