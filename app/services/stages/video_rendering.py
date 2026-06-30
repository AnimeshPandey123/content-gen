"""Placeholder video rendering stage."""

from pathlib import Path

from app.config import get_settings
from app.models.pipeline import RenderResult, ScriptPlan
from app.models.video_project import VideoProject
from app.workflows.stage import Stage


class VideoRenderingStage(Stage[ScriptPlan, RenderResult]):
    """Assemble assets and render a vertical MP4 (placeholder)."""

    @property
    def name(self) -> str:
        return "video_rendering"

    def run(self, input_model: ScriptPlan) -> RenderResult:
        settings = get_settings()
        storyboard_result = input_model.storyboard_result
        document = storyboard_result.content_plan.document

        output_dir = Path(settings.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        video_path = str(output_dir / f"{document.id}.mp4")

        project = VideoProject(
            document=document,
            storyboard=storyboard_result.storyboard,
            script=input_model.script,
            output_path=video_path,
        )

        # Placeholder: no actual video file is written yet.
        return RenderResult(project=project, video_path=video_path, success=True)
