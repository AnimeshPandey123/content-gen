"""Unit tests for render project layout and bootstrap."""

from pathlib import Path

from app.config import Settings
from app.models.pipeline import ContentPlan, ScriptPlan, StoryboardResult
from app.models.render import RenderProject
from app.models.script import Script, ScriptScene, ScriptShot
from app.models.section import Section
from app.models.storyboard import Storyboard
from app.render.project import (
    audio_path,
    bootstrap_render_project,
    scene_basename,
    screenshot_path,
    shot_screenshot_path,
    subtitle_path,
)

from tests.conftest import sample_scene
from tests.test_stages import _sample_document


def _script_plan() -> ScriptPlan:
    document = _sample_document()
    return ScriptPlan(
        storyboard_result=StoryboardResult(
            content_plan=ContentPlan(
                document=document,
                selected_sections=[
                    Section(id="sec-1", title="T", content="Sample", page_numbers=[1]),
                ],
            ),
            storyboard=Storyboard(document_id=document.id, scenes=[sample_scene(id="scene-1")]),
        ),
        script=Script(
            scenes=[
                ScriptScene(
                    scene=1,
                    scene_id="scene-1",
                    shots=[
                        ScriptShot(shot_order=0, voice="Voice", overlay="Overlay"),
                    ],
                ),
            ],
        ),
    )


def _render_project(*, output_dir: Path | None = None) -> RenderProject:
    return bootstrap_render_project(
        _script_plan(),
        settings=Settings(output_dir=output_dir or Path("/tmp/output")),
    )


def test_scene_basename_uses_scene_number() -> None:
    assert scene_basename(1) == "scene01"


def test_asset_paths_follow_project_layout(tmp_path: Path) -> None:
    project_dir = tmp_path / "proj"
    assert screenshot_path(project_dir, 1).name == "scene01.png"
    assert shot_screenshot_path(project_dir, 1, 0).name == "scene01_shot01.png"
    assert audio_path(project_dir, 1).name == "scene01.wav"
    assert subtitle_path(project_dir, 1).name == "scene01.ass"


def test_bootstrap_exports_storyboard_json(tmp_path: Path) -> None:
    project = bootstrap_render_project(_script_plan(), settings=Settings(output_dir=tmp_path))
    storyboard_file = Path(project.storyboard_path)

    assert storyboard_file.exists()
    assert project.scenes[0].scene_number == 1
    assert project.scenes[0].screenshot_path is None
