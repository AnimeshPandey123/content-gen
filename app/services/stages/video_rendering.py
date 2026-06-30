"""Placeholder video rendering stage."""

from pathlib import Path

from app.config import get_settings
from app.models.pipeline import CaptionPlan, RenderResult
from app.models.video_project import VideoProject
from app.workflows.stage import Stage


class VideoRenderingStage(Stage[CaptionPlan, RenderResult]):
    """Assemble assets and render a vertical MP4 (placeholder)."""

    @property
    def name(self) -> str:
        return "video_rendering"

    def run(self, input_model: CaptionPlan) -> RenderResult:
        settings = get_settings()
        narration_plan = input_model.narration_plan
        screenshot_plan = narration_plan.screenshot_plan
        storyboard_result = screenshot_plan.storyboard_result
        document = storyboard_result.content_plan.document

        output_dir = Path(settings.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        video_path = str(output_dir / f"{document.id}.mp4")

        project = VideoProject(
            document=document,
            storyboard=storyboard_result.storyboard,
            screenshot_regions=screenshot_plan.regions,
            narrations=narration_plan.narrations,
            captions=input_model.captions,
            output_path=video_path,
        )

        # Placeholder: no actual video file is written yet.
        return RenderResult(project=project, video_path=video_path, success=True)
