"""Project layout and storyboard export for rendering assets."""

import json
from pathlib import Path

from app.config import Settings, get_settings
from app.models.pipeline import ScriptPlan
from app.models.render import RenderProject, SceneAssets


def scene_basename(scene_number: int) -> str:
    """Return the canonical asset basename for a scene."""
    return f"scene{scene_number:02d}"


def screenshot_path(project_dir: Path, scene_number: int) -> Path:
    return project_dir / "screenshots" / f"{scene_basename(scene_number)}.png"


def audio_path(project_dir: Path, scene_number: int) -> Path:
    return project_dir / "audio" / f"{scene_basename(scene_number)}.wav"


def subtitle_path(project_dir: Path, scene_number: int) -> Path:
    return project_dir / "subtitles" / f"{scene_basename(scene_number)}.ass"


def clip_path(project_dir: Path, scene_number: int) -> Path:
    return project_dir / "clips" / f"{scene_basename(scene_number)}.mp4"


def final_video_path(project_dir: Path, document_id: str) -> Path:
    return project_dir / f"{document_id}.mp4"


def bootstrap_render_project(
    script_plan: ScriptPlan,
    *,
    settings: Settings | None = None,
) -> RenderProject:
    """Create the project folder, export storyboard.json, and seed scene assets."""
    settings = settings or get_settings()
    document = script_plan.storyboard_result.content_plan.document
    project_dir = settings.output_dir / document.id
    project_dir.mkdir(parents=True, exist_ok=True)

    storyboard_file = project_dir / "storyboard.json"
    storyboard_file.write_text(
        json.dumps(
            {
                "document_id": document.id,
                "storyboard": script_plan.storyboard_result.storyboard.model_dump(),
                "script": script_plan.script.model_dump(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    scenes = [
        SceneAssets(scene_number=script_scene.scene, scene_id=script_scene.scene_id)
        for script_scene in script_plan.script.scenes
    ]
    return RenderProject(
        script_plan=script_plan,
        project_dir=str(project_dir.resolve()),
        storyboard_path=str(storyboard_file.resolve()),
        scenes=scenes,
    )
