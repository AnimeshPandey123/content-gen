"""Unit tests for script models."""

import pytest
from app.models.script import Script, ScriptScene, ScriptShot
from pydantic import ValidationError


def test_script_scene_requires_shots() -> None:
    scene = ScriptScene(
        scene=1,
        scene_id="scene-1",
        shots=[
            ScriptShot(
                shot_order=0,
                voice="This paper proposes a new training method.",
                overlay="Train with Less Data",
            ),
            ScriptShot(
                shot_order=1,
                voice="It cuts compute in half.",
                overlay="Half the Compute",
            ),
        ],
    )
    assert scene.overlay == "Train with Less Data"
    assert "training method" in scene.voice
    assert "compute" in scene.voice


def test_script_requires_scenes() -> None:
    with pytest.raises(ValidationError):
        Script(scenes=[])
